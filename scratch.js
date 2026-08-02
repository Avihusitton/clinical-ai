
    (() => {
      "use strict";

      const state = {
        users: [],
        conversations: [],
        activeUserId: "",
        activeConversationId: "",
        activeConversation: null,
        aiAvailable: true,
        busy: false
      };

      const byId = (id) => document.getElementById(id);
      const userSelect = byId("userSelect");
      const conversationList = byId("conversationList");
      const timeline = byId("messageTimeline");
      const questionInput = byId("question");
      const askButton = byId("askButton");
      const useAi = byId("useAi");
      const aiModel = byId("aiModel");
      const privacyCheck = byId("confirmNoPatientData");

      function safeArray(value) {
        return Array.isArray(value) ? value : [];
      }

      function pickObject(payload, key) {
        if (payload && typeof payload[key] === "object" && !Array.isArray(payload[key])) {
          return payload[key];
        }
        return payload && typeof payload === "object" ? payload : {};
      }

      async function api(url, options = {}) {
        const response = await fetch(url, {
          cache: "no-store",
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
          }
        });
        let data = {};
        try {
          data = await response.json();
        } catch {
          data = {};
        }
        if (!response.ok) {
          const error = new Error(data.answer_text || data.message || "לא ניתן להשלים את הפעולה.");
          error.payload = data;
          throw error;
        }
        return data;
      }

      function formatDate(value) {
        if (!value) return "";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "";
        return new Intl.DateTimeFormat("he-IL", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit"
        }).format(date);
      }

      function formatDuration(milliseconds) {
        const number = Number(milliseconds || 0);
        if (!Number.isFinite(number) || number <= 0) return "פחות משנייה";
        if (number < 1000) return `${Math.round(number)} אלפיות שנייה`;
        if (number < 10000) return `${(number / 1000).toFixed(1)} שנ׳`;
        return `${Math.round(number / 1000)} שנ׳`;
      }

      function formatShekels(value) {
        const amount = Number(value || 0);
        if (!Number.isFinite(amount) || amount <= 0) return "₪0.0000";
        if (amount < 1) return `₪${amount.toFixed(4)}`;
        return `₪${amount.toFixed(2)}`;
      }

      function metadataFor(message) {
        const metadata = message && typeof message.metadata === "object"
          ? message.metadata : {};
        const generation = metadata && typeof metadata.generation === "object"
          ? metadata.generation : {};
        return {
          ...metadata,
          ...generation,
          response_type:
            metadata.response_type ||
            message.response_type ||
            generation.response_type ||
            ""
        };
      }

      function costFor(message) {
        if (!message || message.role !== "assistant") return 0;
        const metadata = metadataFor(message);
        const value =
          metadata.cost_ils ??
          metadata.estimated_cost_ils ??
          metadata.cost_nis ??
          0;
        const cost = Number(value);
        return Number.isFinite(cost) ? cost : 0;
      }

      function showToast(message) {
        const toast = byId("toast");
        toast.textContent = message;
        toast.classList.remove("hidden");
        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3200);
      }

      function showComposerError(message) {
        const banner = byId("composerError");
        banner.textContent = message;
        banner.classList.remove("hidden");
      }

      function clearComposerError() {
        byId("composerError").classList.add("hidden");
        byId("composerError").textContent = "";
      }

      function setBusy(busy) {
        state.busy = busy;
        askButton.disabled = busy;
        byId("addUserButton").disabled = busy;
        byId("newConversationButton").disabled = busy;
        askButton.querySelector("span").textContent = busy ? "בונה מענה…" : "שליחה";
      }

      function renderUsers() {
        userSelect.replaceChildren();
        if (!state.users.length) {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "עדיין אין משתמשים";
          userSelect.append(option);
          state.activeUserId = "";
          return;
        }
        for (const user of state.users) {
          const option = document.createElement("option");
          option.value = String(user.id || "");
          option.textContent = String(user.name || "משתמש");
          userSelect.append(option);
        }
        const exists = state.users.some((user) => String(user.id) === state.activeUserId);
        if (!exists) state.activeUserId = String(state.users[0].id || "");
        userSelect.value = state.activeUserId;
      }

      function conversationButton(conversation) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "conversation-item";
        if (String(conversation.id) === state.activeConversationId) {
          button.classList.add("active");
        }
        button.dataset.conversationId = String(conversation.id || "");

        const title = document.createElement("strong");
        title.textContent = String(conversation.title || "שיחה חדשה");
        const meta = document.createElement("span");
        const count = Number(conversation.message_count ?? safeArray(conversation.messages).length);
        const date = formatDate(conversation.updated_at);
        meta.textContent = `${count} הודעות${date ? ` · ${date}` : ""}`;
        button.append(title, meta);
        button.addEventListener("click", () => selectConversation(button.dataset.conversationId));
        return button;
      }

      function renderConversations() {
        conversationList.replaceChildren();
        if (!state.activeUserId) {
          conversationList.innerHTML =
            '<div class="empty-state">הוסיפו משתמש כדי לפתוח סביבת עבודה אישית.</div>';
          return;
        }
        if (!state.conversations.length) {
          conversationList.innerHTML =
            '<div class="empty-state">אין כאן שיחות עדיין.<br>אפשר להתחיל בשיחה חדשה.</div>';
          return;
        }
        for (const conversation of state.conversations) {
          conversationList.append(conversationButton(conversation));
        }
      }

      function evidenceData(message) {
        const metadata = message && typeof message.metadata === "object"
          ? message.metadata : {};
        const evidence = metadata.evidence && typeof metadata.evidence === "object"
          ? metadata.evidence : {};
        return {
          matches: safeArray(message.matches || metadata.matches || evidence.matches),
          relations: safeArray(
            message.canonical_relations ||
            metadata.canonical_relations ||
            evidence.canonical_relations ||
            evidence.relations
          ),
          sources: safeArray(
            message.approved_source_evidence ||
            metadata.approved_source_evidence ||
            evidence.approved_source_evidence
          )
        };
      }

      function evidenceList(title, items, describe) {
        const group = document.createElement("div");
        group.className = "evidence-group";
        const heading = document.createElement("strong");
        heading.textContent = title;
        group.append(heading);
        if (!items.length) {
          const empty = document.createElement("span");
          empty.textContent = "לא נשמרו פריטים להצגה.";
          group.append(empty);
          return group;
        }
        const list = document.createElement("ul");
        for (const item of items.slice(0, 24)) {
          const row = document.createElement("li");
          row.textContent = describe(item);
          list.append(row);
        }
        group.append(list);
        return group;
      }

      function buildEvidence(message) {
        const data = evidenceData(message);
        const details = document.createElement("details");
        details.className = "evidence";
        const summary = document.createElement("summary");
        summary.textContent = "פרטי הראיות והקשרים ששימשו למענה";
        const content = document.createElement("div");
        content.className = "evidence-content";
        content.append(
          evidenceList("ידע קנוני מאושר", data.matches, (item) =>
            `${item.entry_name || item.name || "מושג"}${item.card_id ? ` (${item.card_id})` : ""}`
          ),
          evidenceList("קשרים מאושרים", data.relations, (item) =>
            [
              item.source_name || item.source_label || "",
              item.relation_label || item.relation_type || "קשור אל",
              item.target_name || item.target_label || ""
            ].filter(Boolean).join(" — ")
          ),
          evidenceList("מראי־מקום מאושרים", data.sources, (item) =>
            [
              item.source_document_id || item.entry_name || "מקור שיטה",
              item.evidence_locator || "",
              item.source_authority || ""
            ].filter(Boolean).join(" — ")
          )
        );
        details.append(summary, content);
        return details;
      }

      function buildMessage(message) {
        const isAssistant = message.role === "assistant";
        const metadata = metadataFor(message);
        const isClarification =
          isAssistant &&
          ["needs_clarification", "clarification"].includes(String(metadata.response_type));
        const article = document.createElement("article");
        article.className = `message ${isAssistant ? "assistant" : "user"}`;
        if (isClarification) article.classList.add("clarification");

        const label = document.createElement("div");
        label.className = "message-label";
        const author = document.createElement("strong");
        author.textContent = isAssistant
          ? (isClarification ? "שאלת הבהרה" : "דרך")
          : "העדכון שלך";
        const time = document.createElement("span");
        time.textContent = formatDate(message.created_at);
        label.append(author, time);

        const body = document.createElement("div");
        body.className = "message-body";
        if (isClarification) {
          const ribbon = document.createElement("div");
          ribbon.className = "clarification-ribbon";
          ribbon.textContent = "נדרש עוד מידע לפני גיבוש כיוון";
          body.append(ribbon);
        }
        const content = document.createElement("div");
        content.textContent = String(message.content || message.answer_text || "");
        body.append(content);

        article.append(label, body);

        if (isAssistant) {
          const metrics = document.createElement("div");
          metrics.className = "answer-metrics";
          const cost = document.createElement("span");
          cost.className = "answer-metric cost";
          cost.textContent = `עלות ${formatShekels(costFor(message))}`;
          const duration = document.createElement("span");
          duration.className = "answer-metric";
          duration.textContent = `זמן הפקה ${formatDuration(metadata.elapsed_ms)}`;
          metrics.append(cost, duration);
          if (metadata.quality_reviewed) {
            const reviewed = document.createElement("span");
            reviewed.className = "answer-metric";
            reviewed.textContent = "עבר בקרת איכות";
            metrics.append(reviewed);
          }
          article.append(metrics, buildEvidence(message));
        }
        return article;
      }

      function renderConversation() {
        const conversation = state.activeConversation;
        if (!conversation) {
          byId("activeConversationTitle").textContent = "שיחה חדשה";
          byId("activeConversationMeta").textContent = "ההקשר נבנה בהדרגה לאורך השיחה";
          byId("conversationCost").textContent = "₪0.0000";
          timeline.innerHTML = `
            <div class="timeline-welcome">
              <h3>מתחילים מן השאלה הנכונה</h3>
              <p>כתבו שאלה על השיטה או עדכון המשך בשיחה קיימת. המערכת תאתר הקשר מצומצם מן הידע הקנוני, ואם חסר מידע מהותי היא תחזור אליכם בשאלות הבהרה.</p>
              <div class="path-line" aria-hidden="true"></div>
            </div>`;
          return;
        }

        const messages = safeArray(conversation.messages);
        byId("activeConversationTitle").textContent =
          String(conversation.title || "שיחה חדשה");
        byId("activeConversationMeta").textContent = messages.length
          ? `${messages.length} הודעות · נשמר מקומית`
          : "ההקשר נבנה בהדרגה לאורך השיחה";

        timeline.replaceChildren();
        if (!messages.length) {
          timeline.innerHTML = `
            <div class="timeline-welcome">
              <h3>השיחה מוכנה</h3>
              <p>אפשר להתחיל בשאלה, או לתאר עדכון שאינו כולל פרטים מזהים. אם חסר מידע מכריע, תופיע שאלת הבהרה לפני גיבוש האסטרטגיה.</p>
              <div class="path-line" aria-hidden="true"></div>
            </div>`;
        } else {
          for (const message of messages) timeline.append(buildMessage(message));
        }

        const total = messages.reduce((sum, message) => sum + costFor(message), 0);
        byId("conversationCost").textContent = formatShekels(total);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      async function loadWorkspace() {
        const payload = await api("/api/workspace");
        state.users = safeArray(payload.users || payload);
        const savedUserId = window.localStorage.getItem("derech.activeUserId") || "";
        state.activeUserId = state.users.some((user) => String(user.id) === savedUserId)
          ? savedUserId
          : String(state.users[0]?.id || "");
        renderUsers();
        await loadConversations();
      }

      async function loadConversations(preferredConversationId = "") {
        state.activeConversation = null;
        if (!state.activeUserId) {
          state.conversations = [];
          state.activeConversationId = "";
          renderConversations();
          renderConversation();
          return;
        }
        const payload = await api(
          `/api/conversations?user_id=${encodeURIComponent(state.activeUserId)}`
        );
        state.conversations = safeArray(payload.conversations || payload);
        const savedConversationId =
          preferredConversationId ||
          window.localStorage.getItem(`derech.activeConversationId.${state.activeUserId}`) ||
          "";
        const exists = state.conversations.some(
          (conversation) => String(conversation.id) === savedConversationId
        );
        state.activeConversationId = exists
          ? savedConversationId
          : String(state.conversations[0]?.id || "");
        renderConversations();
        if (state.activeConversationId) {
          await loadConversation(state.activeConversationId);
        } else {
          renderConversation();
        }
      }

      async function loadConversation(conversationId) {
        if (!state.activeUserId || !conversationId) return;
        const payload = await api(
          `/api/conversation?user_id=${encodeURIComponent(state.activeUserId)}` +
          `&conversation_id=${encodeURIComponent(conversationId)}`
        );
        state.activeConversation = pickObject(payload, "conversation");
        state.activeConversationId = String(
          state.activeConversation.id || conversationId
        );
        window.localStorage.setItem(
          `derech.activeConversationId.${state.activeUserId}`,
          state.activeConversationId
        );
        renderConversations();
        renderConversation();
      }

      async function selectConversation(conversationId) {
        if (state.busy || conversationId === state.activeConversationId) return;
        clearComposerError();
        try {
          await loadConversation(conversationId);
        } catch (error) {
          showToast(error.message);
        }
      }

      async function createUser() {
        const input = byId("newUserName");
        const name = input.value.trim();
        if (!name || state.busy) {
          if (!name) showToast("יש להזין שם למשתמש החדש.");
          return;
        }
        setBusy(true);
        try {
          const payload = await api("/api/users", {
            method: "POST",
            body: JSON.stringify({name})
          });
          const user = pickObject(payload, "user");
          input.value = "";
          state.activeUserId = String(user.id || "");
          window.localStorage.setItem("derech.activeUserId", state.activeUserId);
          await loadWorkspace();
          showToast("סביבת העבודה נוספה.");
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function createConversation() {
        if (!state.activeUserId) {
          showToast("יש להוסיף או לבחור משתמש לפני פתיחת שיחה.");
          return;
        }
        if (state.busy) return;
        setBusy(true);
        clearComposerError();
        try {
          const payload = await api("/api/conversations", {
            method: "POST",
            body: JSON.stringify({
              user_id: state.activeUserId,
              title: "שיחה חדשה"
            })
          });
          const conversation = pickObject(payload, "conversation");
          const conversationId = String(conversation.id || "");
          await loadConversations(conversationId);
          questionInput.focus();
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function ensureConversation() {
        if (state.activeConversationId) return state.activeConversationId;
        const payload = await api("/api/conversations", {
          method: "POST",
          body: JSON.stringify({
            user_id: state.activeUserId,
            title: "שיחה חדשה"
          })
        });
        const conversation = pickObject(payload, "conversation");
        const conversationId = String(conversation.id || "");
        state.activeConversationId = conversationId;
        return conversationId;
      }

      async function ask() {
        const question = questionInput.value.trim();
        clearComposerError();
        if (state.busy) return;
        if (!state.activeUserId) {
          showComposerError("יש להוסיף או לבחור משתמש לפני שליחת שאלה.");
          return;
        }
        if (!question) {
          showComposerError("יש לכתוב שאלה או עדכון.");
          questionInput.focus();
          return;
        }
        if (!privacyCheck.checked) {
          showComposerError("יש לאשר שהטקסט אינו כולל שמות או פרטים מזהים.");
          privacyCheck.focus();
          return;
        }

        setBusy(true);
        try {
          const conversationId = await ensureConversation();
          const payload = await api("/api/ask", {
            method: "POST",
            body: JSON.stringify({
              user_id: state.activeUserId,
              conversation_id: conversationId,
              question,
              use_ai: useAi.checked,
              ai_model: aiModel.value,
              confirmed_no_patient_data: true
            })
          });
          if (payload.status && !["answered", "ok"].includes(payload.status)) {
            throw new Error(payload.answer_text || "לא ניתן להשלים את המענה.");
          }
          questionInput.value = "";
          await loadConversations(conversationId);
        } catch (error) {
          showComposerError(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function checkHealth() {
        const status = byId("systemStatus");
        try {
          const data = await api("/api/health");
          state.aiAvailable = Boolean(data.ai_available);
          useAi.disabled = !state.aiAvailable;
          aiModel.disabled = !state.aiAvailable || !useAi.checked;
          if (!state.aiAvailable) useAi.checked = false;
          status.classList.toggle("ready", Boolean(data.neo4j_running));
          status.querySelector("span:last-child").textContent =
            data.neo4j_running ? "רשת הידע מחוברת" : "רשת הידע אינה זמינה";
        } catch {
          status.querySelector("span:last-child").textContent = "המנוע המקומי אינו זמין";
          useAi.disabled = true;
          aiModel.disabled = true;
        }
      }

      userSelect.addEventListener("change", async () => {
        state.activeUserId = userSelect.value;
        state.activeConversationId = "";
        window.localStorage.setItem("derech.activeUserId", state.activeUserId);
        clearComposerError();
        try {
          await loadConversations();
        } catch (error) {
          showToast(error.message);
        }
      });

      byId("addUserButton").addEventListener("click", createUser);
      byId("newUserName").addEventListener("keydown", (event) => {
        if (event.key === "Enter") createUser();
      });
      byId("newConversationButton").addEventListener("click", createConversation);
      askButton.addEventListener("click", ask);
      questionInput.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") ask();
      });
      useAi.addEventListener("change", () => {
        aiModel.disabled = !state.aiAvailable || !useAi.checked;
      });

      Promise.allSettled([checkHealth(), loadWorkspace()]).then((results) => {
        const workspaceResult = results[1];
        if (workspaceResult.status === "rejected") {
          showToast("לא ניתן לטעון את מרחב העבודה המקומי.");
        }
      });
    })();
  