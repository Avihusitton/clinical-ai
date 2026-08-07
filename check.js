
    (() => {
      "use strict";

      const state = {
        therapists: [],
        activeTherapistId: "",
        patients: [],
        activePatientId: "",
        activeConversationId: "",
        activeConversation: null,
        aiAvailable: true,
        busy: false
      };

      const byId = (id) => document.getElementById(id);
      const therapistSelect = byId("therapistSelect");
      const editTherapistButton = byId("editTherapistButton");
      const addTherapistForm = byId("addTherapistForm");
      const showAddTherapistButton = byId("showAddTherapistButton");
      const newTherapistName = byId("newTherapistName");
      const addTherapistButton = byId("addTherapistButton");
      const patientList = byId("patientList");
      const timeline = byId("messageTimeline");
      const questionInput = byId("question");
      const askButton = byId("askButton");
      const useAi = byId("useAi");
      const aiModel = byId("aiModel");
      const privacyCheck = byId("confirmNoPatientData");
      const addPatientForm = byId("addPatientForm");
      const showAddPatientButton = byId("showAddPatientButton");
      const newPatientName = byId("newPatientName");

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
          if (data && data.status === "conversation_or_patient_not_found") {
            state.activeConversationId = null;
            state.activePatientId = null;
            saveState();
            window.location.reload();
            return;
          }
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
        if (!message || message.role === "user") return 0;
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
        addTherapistButton.disabled = busy;
        byId("addPatientButton").disabled = busy;
        askButton.querySelector("span").textContent = busy ? "בונה מענה…" : "שליחה";
      }
      
      function showLoadingMessage() {
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "message system";
        loadingDiv.id = "temporaryLoadingMessage";
        loadingDiv.innerHTML = `
          <div class="message-meta">מערכת</div>
          <div class="message-body" style="text-align: right; direction: rtl;">
            <div class="typing-indicator" style="display: inline-block;">
              <span></span><span></span><span></span>
            </div>
            <span id="loadingProgressText" style="margin-right: 8px; font-size: 0.9em; color: var(--muted);">הסוכן מנתח את הבקשה ומעבד את התשובה...</span>
          </div>
        `;
        timeline.append(loadingDiv);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      function removeLoadingMessage() {
        const el = byId("temporaryLoadingMessage");
        if (el) el.remove();
      }
      function escapeHtml(unsafe) {
        if (!unsafe) return "";
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;")
             .replace(/\n/g, "<br>");
      }

      function appendOptimisticMessage(content) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message user optimistic";
        msgDiv.id = "temporaryUserMessage";
        msgDiv.innerHTML = `
          <div class="message-meta">אני</div>
          <div class="message-body">${escapeHtml(content)}</div>
        `;
        timeline.append(msgDiv);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      function removeOptimisticMessage() {
        const el = byId("temporaryUserMessage");
        if (el) el.remove();
      }

      async function renderPatients() {
        patientList.replaceChildren();
        if (!state.patients.length) {
          patientList.innerHTML = '<div class="empty-state">עדיין אין מטופלים.</div>';
          state.activePatientId = "";
          return;
        }

        for (const patient of state.patients) {
          const patientId = String(patient.id || "");
          
          const item = document.createElement("div");
          item.className = "patient-item";

          const header = document.createElement("div");
          header.className = "patient-header";
          
          const headerText = document.createElement("span");
          headerText.textContent = String(patient.name || "מטופל אנונימי");
          headerText.style.flex = "1";
          
          const editPatientBtn = document.createElement("button");
          editPatientBtn.className = "quiet-button";
          editPatientBtn.innerHTML = "✏️";
          editPatientBtn.style.padding = "2px 6px";
          editPatientBtn.style.fontSize = "0.9rem";
          editPatientBtn.title = "עריכת שם מטופל";
          editPatientBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const newName = prompt("הכנס שם חדש למטופל:", patient.name);
            if (newName && newName.trim() !== "" && newName !== patient.name) {
              setBusy(true);
              try {
                await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patientId)}`, {
                  method: "PUT",
                  body: JSON.stringify({name: newName.trim()})
                });
                await loadWorkspace();
              } catch(err) {
                showToast(err.message);
              } finally {
                setBusy(false);
              }
            }
          });
          
          header.append(headerText, editPatientBtn);
          
          const convContainer = document.createElement("div");
          convContainer.className = "patient-conversations";
          
          // New conversation button specifically for this patient
          const newConvBtn = document.createElement("button");
          newConvBtn.className = "conversation-item";
          newConvBtn.style.color = "var(--olive)";
          newConvBtn.innerHTML = "<strong>+ שיחה חדשה</strong>";
          newConvBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            await createConversation(patientId);
          });
          convContainer.append(newConvBtn);

          // Render the conversations dynamically when opened
          const patientConversations = patient.conversations || [];
          for (const conv of patientConversations) {
            const convBtn = document.createElement("button");
            convBtn.type = "button";
            convBtn.className = "conversation-item";
            convBtn.style.display = "flex";
            convBtn.style.justifyContent = "space-between";
            convBtn.style.alignItems = "center";
            convBtn.style.textAlign = "right";

            if (String(conv.id) === state.activeConversationId && patientId === state.activePatientId) {
              convBtn.classList.add("active");
              header.classList.add("expanded");
              convContainer.classList.add("open");
            }
            
            const infoDiv = document.createElement("div");
            infoDiv.style.flex = "1";
            
            const title = document.createElement("strong");
            title.textContent = String(conv.title || "שיחה");
            const meta = document.createElement("span");
            const count = Number(conv.message_count ?? safeArray(conv.messages).length);
            const date = formatDate(conv.updated_at);
            meta.textContent = `${count} הודעות${date ? ` · ${date}` : ""}`;
            meta.style.display = "block";
            
            infoDiv.append(title, meta);

            const deleteConvBtn = document.createElement("div");
            deleteConvBtn.innerHTML = "🗑️";
            deleteConvBtn.style.fontSize = "1.2rem";
            deleteConvBtn.style.padding = "4px";
            deleteConvBtn.style.color = "var(--danger)";
            deleteConvBtn.style.cursor = "pointer";
            deleteConvBtn.title = "מחיקת שיחה";
            
            deleteConvBtn.addEventListener("click", async (e) => {
              e.stopPropagation();
              if (confirm(`האם למחוק את השיחה "${title.textContent}"?`)) {
                setBusy(true);
                try {
                  await api(`/api/conversation?therapist_id=${encodeURIComponent(state.activeTherapistId)}&patient_id=${encodeURIComponent(patientId)}&conversation_id=${encodeURIComponent(conv.id)}`, { method: "DELETE" });
                  if (state.activeConversationId === String(conv.id)) {
                    state.activeConversationId = "";
                    window.localStorage.removeItem("derech.activeConversationId");
                    timeline.replaceChildren();
                  }
                  await updateState();
                } catch (err) {
                  alert("שגיאה במחיקת שיחה");
                } finally {
                  setBusy(false);
                }
              }
            });

            convBtn.append(infoDiv, deleteConvBtn);
            
            convBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              state.activePatientId = patientId;
              window.localStorage.setItem("derech.activePatientId", patientId);
              selectConversation(patientId, String(conv.id));
            });
            convContainer.append(convBtn);
          }

          header.addEventListener("click", () => {
            const isOpen = convContainer.classList.contains("open");
            if (!isOpen) {
               // close others
               document.querySelectorAll(".patient-conversations").forEach(el => el.classList.remove("open"));
               document.querySelectorAll(".patient-header").forEach(el => el.classList.remove("expanded"));
               
               convContainer.classList.add("open");
               header.classList.add("expanded");
               state.activePatientId = patientId;
               window.localStorage.setItem("derech.activePatientId", patientId);
            } else {
               convContainer.classList.remove("open");
               header.classList.remove("expanded");
            }
          });

          item.append(header, convContainer);
          patientList.append(item);
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

      async function fetchModels() {
        console.log("Fetching models...");
        try {
          const mPayload = await api("/api/models");
          console.log("Models payload:", mPayload);
          if (mPayload.models) {
            const select = byId("aiModel");
            // Keep the 'auto' option, remove others
            select.innerHTML = '<option value="auto" selected>בחירה אוטומטית (מומלץ)</option>';
            if (mPayload.models.pro) {
              const opt = document.createElement("option");
              opt.value = mPayload.models.pro.id;
              opt.textContent = `${mPayload.models.pro.name} · מעמיק`;
              select.appendChild(opt);
            }
            if (mPayload.models.fast) {
              const opt = document.createElement("option");
              opt.value = mPayload.models.fast.id;
              opt.textContent = `${mPayload.models.fast.name} · מהיר`;
              select.appendChild(opt);
            }
          }
        } catch (e) {
          console.error("Failed to load models", e);
        }
      }

      async function loadWorkspace() {
        fetchModels();
        try {
          const tPayload = await api("/api/therapists");
          state.therapists = safeArray(tPayload.therapists || tPayload);
        } catch (e) {
          state.therapists = [];
        }

        const savedTherapistId = window.localStorage.getItem("derech.activeTherapistId") || "";
        state.activeTherapistId = state.therapists.some((t) => String(t.id) === savedTherapistId)
          ? savedTherapistId
          : String(state.therapists[0]?.id || "");

        therapistSelect.replaceChildren();
        if (state.therapists.length) {
          for (const t of state.therapists) {
            const opt = document.createElement("option");
            opt.value = t.id;
            opt.textContent = t.name;
            therapistSelect.append(opt);
          }
          therapistSelect.value = state.activeTherapistId;
          therapistSelect.disabled = false;
        } else {
          const opt = document.createElement("option");
          opt.textContent = "אין מטפלים";
          therapistSelect.append(opt);
          therapistSelect.disabled = true;
          state.patients = [];
          renderPatients();
          return;
        }

        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients`);
          state.patients = safeArray(payload.patients || payload);
        } catch (e) {
          state.patients = [];
        }

        // For each patient, load their conversations so we can render the accordion fully
        for (const patient of state.patients) {
          try {
            const convPayload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patient.id)}/conversations`);
            patient.conversations = safeArray(convPayload.conversations || convPayload);
          } catch (e) {
            patient.conversations = [];
          }
        }

        const savedPatientId = window.localStorage.getItem("derech.activePatientId") || "";
        state.activePatientId = state.patients.some((p) => String(p.id) === savedPatientId)
          ? savedPatientId
          : String(state.patients[0]?.id || "");

        // If we have a patient, we also try to restore their active conversation
        if (state.activePatientId) {
          const savedConversationId = window.localStorage.getItem(`derech.activeConversationId.${state.activePatientId}`) || "";
          state.activeConversationId = savedConversationId;
          if (state.activeConversationId) {
            await loadConversation(state.activePatientId, state.activeConversationId);
          }
        }
        
        renderPatients();
        if (!state.activeConversationId) renderConversation();
      }

      async function loadConversation(patientId, conversationId) {
        if (!state.activeTherapistId || !patientId || !conversationId) return;
        try {
          const payload = await api(`/api/conversation?therapist_id=${encodeURIComponent(state.activeTherapistId)}&patient_id=${encodeURIComponent(patientId)}&conversation_id=${encodeURIComponent(conversationId)}`);
          if (payload.conversation) {
             state.activeConversation = payload.conversation;
             state.activeConversationId = String(conversationId);
             window.localStorage.setItem(`derech.activeConversationId.${patientId}`, state.activeConversationId);
             renderPatients();
             renderConversation();
          }
        } catch (e) {
          console.error(e);
        }
      }

      async function selectConversation(patientId, conversationId) {
        if (state.busy || (conversationId === state.activeConversationId && patientId === state.activePatientId)) return;
        clearComposerError();
        try {
          await loadConversation(patientId, conversationId);
        } catch (error) {
          showToast(error.message);
        }
      }

      async function createPatient() {
        const name = newPatientName.value.trim();
        if (!name || state.busy) {
          if (!name) showToast("יש להזין שם למטופל החדש.");
          return;
        }
        setBusy(true);
        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients`, {
            method: "POST",
            body: JSON.stringify({name})
          });
          const patient = pickObject(payload, "patient");
          newPatientName.value = "";
          addPatientForm.classList.add("hidden");
          state.activePatientId = String(patient.id || "");
          window.localStorage.setItem("derech.activePatientId", state.activePatientId);
          await loadWorkspace();
          showToast("המטופל נוסף בהצלחה.");
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function createConversation(patientId) {
        if (!patientId) {
          showToast("יש להוסיף או לבחור מטופל לפני פתיחת שיחה.");
          return;
        }
        if (state.busy) return;
        setBusy(true);
        clearComposerError();
        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patientId)}/conversations`, {
            method: "POST",
            body: JSON.stringify({
              title: "שיחה חדשה"
            })
          });
          const conversation = pickObject(payload, "conversation");
          const conversationId = String(conversation.id || "");
          state.activePatientId = patientId;
          await loadWorkspace();
          await selectConversation(patientId, conversationId);
          questionInput.focus();
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function ensureConversation() {
        if (state.activeConversationId) return state.activeConversationId;
        const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(state.activePatientId)}/conversations`, {
          method: "POST",
          body: JSON.stringify({
            title: "שיחה חדשה"
          })
        });
        const conversation = pickObject(payload, "conversation");
        const conversationId = String(conversation.id || "");
        state.activeConversationId = conversationId;
        await loadWorkspace();
        return conversationId;
      }

      async function ask() {
        const question = questionInput.value.trim();
        clearComposerError();
        if (state.busy) return;
        if (!state.activePatientId) {
          showComposerError("יש להוסיף או לבחור מטופל לפני שליחת שאלה.");
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
        appendOptimisticMessage(question);
        questionInput.value = "";
        showLoadingMessage();
        
        try {
          const conversationId = await ensureConversation();
          
          const res = await fetch("/api/ask", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              therapist_id: state.activeTherapistId,
              patient_id: state.activePatientId,
              conversation_id: conversationId,
              question,
              use_ai: useAi.checked,
              ai_model: aiModel.value === "auto" ? null : aiModel.value,
              auto_route: aiModel.value === "auto",
              confirmed_no_patient_data: true
            })
          });

          if (res.status === 401) {
            showAuthScreen();
            throw new Error("פג תוקף החיבור.");
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let buffer = "";
          let finalPayload = null;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            
            let newlineIndex;
            while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
              const line = buffer.slice(0, newlineIndex).trim();
              buffer = buffer.slice(newlineIndex + 1);
              if (!line) continue;
              
              try {
                const data = JSON.parse(line);
                if (data.progress) {
                  const textSpan = document.getElementById("loadingProgressText");
                  if (textSpan) {
                    textSpan.textContent = data.progress;
                  }
                } else if (data.status) {
                  finalPayload = data;
                }
              } catch (e) {
                console.error("Parse error", e);
              }
            }
          }
          
          if (!finalPayload) {
            throw new Error("לא התקבלה תשובה תקינה מהשרת.");
          }
          const payload = finalPayload;

          if (payload.status_code && payload.status_code !== 200) {
             throw new Error(payload.answer_text || "שגיאה בשרת.");
          }
          if (payload.status && !["answered", "ok"].includes(payload.status)) {
            throw new Error(payload.answer_text || "לא ניתן להשלים את המענה.");
          }
          removeOptimisticMessage();
          removeLoadingMessage();
          await loadWorkspace();
          await selectConversation(state.activePatientId, conversationId);
        } catch (error) {
          showComposerError(error.message);
          questionInput.value = question;
          removeOptimisticMessage();
          removeLoadingMessage();
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

      therapistSelect.addEventListener("change", async () => {
        state.activeTherapistId = therapistSelect.value;
        window.localStorage.setItem("derech.activeTherapistId", state.activeTherapistId);
        state.activePatientId = "";
        state.activeConversationId = "";
        await loadWorkspace();
      });

      editTherapistButton.addEventListener("click", async () => {
        if (!state.activeTherapistId || state.busy) return;
        const currentTherapist = state.therapists.find(t => String(t.id) === state.activeTherapistId);
        if (!currentTherapist) return;
        
        const newName = prompt("הכנס שם חדש למטפל:", currentTherapist.name);
        if (newName && newName.trim() !== "" && newName !== currentTherapist.name) {
          setBusy(true);
          try {
            await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}`, {
              method: "PUT",
              body: JSON.stringify({name: newName.trim()})
            });
            await loadWorkspace();
          } catch(err) {
            showToast(err.message);
          } finally {
            setBusy(false);
          }
        }
      });

      const deleteTherapistBtn = byId("deleteTherapistButton");
      if (deleteTherapistBtn) {
        deleteTherapistBtn.addEventListener("click", async () => {
          if (!state.activeTherapistId || state.busy) return;
          const currentTherapist = state.therapists.find(t => String(t.id) === state.activeTherapistId);
          if (!currentTherapist) return;
          
          if (confirm(`האם אתה בטוח שברצונך למחוק את המטפל "${currentTherapist.name}"? פעולה זו תמחק גם את כל המטופלים והשיחות המשויכים אליו.`)) {
            setBusy(true);
            try {
              await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}`, {
                method: "DELETE"
              });
              state.activeTherapistId = "";
              window.localStorage.removeItem("derech.activeTherapistId");
              state.activePatientId = "";
              state.activeConversationId = "";
              await loadWorkspace();
            } catch(err) {
              showToast(err.message);
            } finally {
              setBusy(false);
            }
          }
        });
      }

      showAddTherapistButton.addEventListener("click", () => {
        addTherapistForm.classList.toggle("hidden");
        if (!addTherapistForm.classList.contains("hidden")) {
          newTherapistName.focus();
        }
      });

      async function createTherapist() {
        const name = newTherapistName.value.trim();
        if (!name || state.busy) {
          if (!name) showToast("יש להזין שם למטפל החדש.");
          return;
        }
        setBusy(true);
        try {
          const payload = await api("/api/therapists", {
            method: "POST",
            body: JSON.stringify({name})
          });
          const therapist = pickObject(payload, "therapist");
          newTherapistName.value = "";
          addTherapistForm.classList.add("hidden");
          state.activeTherapistId = String(therapist.id || "");
          window.localStorage.setItem("derech.activeTherapistId", state.activeTherapistId);
          await loadWorkspace();
          showToast("המטפל נוסף בהצלחה.");
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      addTherapistButton.addEventListener("click", createTherapist);
      newTherapistName.addEventListener("keydown", (event) => {
        if (event.key === "Enter") createTherapist();
      });

      showAddPatientButton.addEventListener("click", () => {
        addPatientForm.classList.toggle("hidden");
        if (!addPatientForm.classList.contains("hidden")) {
          newPatientName.focus();
        }
      });
      
      byId("addPatientButton").addEventListener("click", createPatient);
      newPatientName.addEventListener("keydown", (event) => {
        if (event.key === "Enter") createPatient();
      });
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

      // Intake logic
      const intakeModal = byId("intakeModal");
      const showIntakeModalButton = byId("showIntakeModalButton");
      const closeIntakeModalButton = byId("closeIntakeModalButton");
      const submitIntakeButton = byId("submitIntakeButton");
      const intakeContent = byId("intakeContent");

      showIntakeModalButton.addEventListener("click", () => {
        intakeModal.classList.add("open");
        intakeContent.focus();
      });

      closeIntakeModalButton.addEventListener("click", () => {
        intakeModal.classList.remove("open");
      });
      
      intakeModal.addEventListener("click", (e) => {
        if (e.target === intakeModal) {
          intakeModal.classList.remove("open");
        }
      });

      // Intake Tabs Logic
      const intakeTabs = document.querySelectorAll('.intake-tab');
      const intakeTabContents = document.querySelectorAll('.intake-tab-content');
      let activeIntakeTab = 'file';

      intakeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          intakeTabs.forEach(t => t.classList.remove('active'));
          intakeTabContents.forEach(c => c.classList.remove('active'));
          
          tab.classList.add('active');
          activeIntakeTab = tab.dataset.tab;
          
          if (activeIntakeTab === 'file') {
            byId('intakeTabFile').classList.add('active');
          } else {
            byId('intakeTabText').classList.add('active');
          }
        });
      });

      // File Drag & Drop Logic
      const dropZone = byId('intakeDropZone');
      const fileInput = byId('intakeFileInput');
      const fileListEl = byId('intakeFileList');
      let intakeFiles = [];

      function renderIntakeFiles() {
        fileListEl.innerHTML = '';
        intakeFiles.forEach((file, index) => {
          const item = document.createElement('div');
          item.className = 'file-item';
          const nameSpan = document.createElement('span');
          nameSpan.textContent = file.name;
          const removeBtn = document.createElement('button');
          removeBtn.type = 'button';
          removeBtn.textContent = '×';
          removeBtn.addEventListener('click', () => {
            intakeFiles.splice(index, 1);
            renderIntakeFiles();
          });
          item.append(nameSpan, removeBtn);
          fileListEl.append(item);
        });
      }

      dropZone.addEventListener('click', () => fileInput.click());
      
      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      });
      dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      });
      async function processDropItems(items) {
        const promises = [];
        
        async function traverseFileTree(item, path) {
          path = path || "";
          if (item.isFile) {
            promises.push(new Promise((resolve) => {
              item.file(file => {
                const ext = file.name.split('.').pop().toLowerCase();
                if (['pdf', 'doc', 'docx', 'txt'].includes(ext)) {
                  intakeFiles.push(file);
                }
                resolve();
              });
            }));
          } else if (item.isDirectory) {
            const dirReader = item.createReader();
            const readEntries = () => new Promise((resolve) => {
              dirReader.readEntries(entries => {
                if (entries.length === 0) resolve([]);
                else readEntries().then(more => resolve(entries.concat(more)));
              });
            });
            const entries = await readEntries();
            for (let i = 0; i < entries.length; i++) {
              await traverseFileTree(entries[i], path + item.name + "/");
            }
          }
        }

        for (let i = 0; i < items.length; i++) {
          const item = items[i].webkitGetAsEntry();
          if (item) {
            await traverseFileTree(item);
          }
        }
        
        await Promise.all(promises);
        renderIntakeFiles();
      }

      dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.items) {
          setBusy(true);
          await processDropItems(e.dataTransfer.items);
          setBusy(false);
        } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          intakeFiles.push(...Array.from(e.dataTransfer.files).filter(f => ['pdf', 'doc', 'docx', 'txt'].includes(f.name.split('.').pop().toLowerCase())));
          renderIntakeFiles();
        }
      });
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          intakeFiles.push(...Array.from(e.target.files));
          renderIntakeFiles();
        }
        fileInput.value = ''; // reset
      });

      submitIntakeButton.addEventListener("click", async () => {
        const order = document.querySelector('input[name="intakeOrder"]:checked').value;
        
        if (activeIntakeTab === 'file' && intakeFiles.length === 0) {
          showToast("נא לבחור קבצים לפני השליחה.");
          return;
        }
        if (activeIntakeTab === 'text' && !intakeContent.value.trim()) {
          showToast("נא להזין תוכן לפני השליחה.");
          return;
        }

        setBusy(true);
        submitIntakeButton.disabled = true;
        submitIntakeButton.textContent = "שולח...";
        
        try {
          if (activeIntakeTab === 'file') {
            const formData = new FormData();
            intakeFiles.forEach(f => formData.append('files', f));
            formData.append('order', order);
            
            const response = await fetch("/api/intake/upload", {
              method: "POST",
              body: formData
            });
            if (!response.ok) {
              const err = await response.json().catch(() => ({}));
              throw new Error(err.message || "שגיאה בהעלאת קבצים");
            }
            showToast("הקבצים הועלו בהצלחה.");
            intakeFiles = [];
            renderIntakeFiles();
            intakeModal.classList.remove("open");
            loadInboxFiles();
          } else {
            const text = intakeContent.value.trim();
            await api("/api/intake", {
              method: "POST",
              body: JSON.stringify({ content: text, order: parseInt(order, 10) })
            });
            showToast("החומר נקלט בהצלחה בתיקיית המערכת (Inbox) וימתין לעיבוד.");
            intakeContent.value = "";
            intakeModal.classList.remove("open");
            loadInboxFiles();
          }
        } catch(err) {
          showToast("שגיאה בהזנת החומר: " + err.message);
        } finally {
          setBusy(false);
          submitIntakeButton.disabled = false;
          submitIntakeButton.textContent = "הזן למערכת";
        }
      });

      // Inbox Section Logic
      const inboxFileListEl = byId('inboxFileList');
      const submitInboxButton = byId('submitInboxButton');
      const refreshInboxButton = byId('refreshInboxButton');
      let currentInboxFiles = [];

      async function loadInboxFiles() {
        try {
          const res = await fetch("/api/inbox/files");
          if (!res.ok) return;
          const data = await res.json();
          currentInboxFiles = data.files || [];
          renderInboxFiles();
        } catch(e) {
          console.error(e);
        }
      }

      function renderInboxFiles() {
        inboxFileListEl.innerHTML = '';
        if (currentInboxFiles.length === 0) {
          inboxFileListEl.innerHTML = '<div class="empty-state">אין קבצים ממתינים בקלט.</div>';
          submitInboxButton.classList.add('hidden');
          return;
        }
        submitInboxButton.classList.remove('hidden');
        currentInboxFiles.forEach((filename, idx) => {
          const item = document.createElement('div');
          item.className = 'inbox-file-item';
          
          const label = document.createElement('label');
          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.checked = true;
          cb.dataset.filename = filename;
          
          const nameSpan = document.createElement('span');
          nameSpan.textContent = filename;
          nameSpan.style.overflow = 'hidden';
          nameSpan.style.textOverflow = 'ellipsis';
          nameSpan.style.whiteSpace = 'nowrap';
          
          label.append(cb, nameSpan);
          
          const select = document.createElement('select');
          select.dataset.idx = idx;
          select.innerHTML = `
            <option value="1">סדר 1</option>
            <option value="2">סדר 2</option>
            <option value="3">סדר 3</option>
          `;
          
          item.append(label, select);
          inboxFileListEl.append(item);
        });
      }

      refreshInboxButton.addEventListener('click', (e) => {
        e.stopPropagation();
        loadInboxFiles();
      });

      submitInboxButton.addEventListener('click', async () => {
        const checkboxes = inboxFileListEl.querySelectorAll('input[type="checkbox"]:checked');
        if (checkboxes.length === 0) {
          showToast("לא נבחרו קבצים להזנה.");
          return;
        }
        
        const filesToProcess = Array.from(checkboxes).map(cb => {
          const filename = cb.dataset.filename;
          const itemEl = cb.closest('.inbox-file-item');
          const selectEl = itemEl.querySelector('select');
          return { filename, order: parseInt(selectEl.value, 10) };
        });
        
        setBusy(true);
        submitInboxButton.disabled = true;
        submitInboxButton.textContent = "מזין...";
        
        try {
          await api("/api/inbox/process", {
            method: "POST",
            body: JSON.stringify({ files: filesToProcess })
          });
          showToast("הקבצים נשלחו לעיבוד בהצלחה.");
          loadInboxFiles();
        } catch(err) {
          showToast("שגיאה בעיבוד קבצי קלט: " + err.message);
        } finally {
          setBusy(false);
          submitInboxButton.disabled = false;
          submitInboxButton.textContent = "הזן נבחרים";
        }
      });
      
      // Load initial inbox state
      loadInboxFiles();

      // Progress polling logic
      const inboxProgressEl = byId('inboxProgress');
      const inboxProgressTextEl = byId('inboxProgressText');
      const inboxProgressBarEl = byId('inboxProgressBar');
      
      async function pollInboxProgress() {
        try {
          const res = await fetch("/api/inbox/progress");
          if (res.ok) {
            const data = await res.json();
            if (data.status === 'processing' || data.status === 'starting') {
              inboxProgressEl.classList.remove('hidden');
              inboxProgressTextEl.textContent = `${data.processed} / ${data.total}`;
              const pct = data.total > 0 ? (data.processed / data.total) * 100 : 0;
              inboxProgressBarEl.style.width = `${pct}%`;
            } else {
              inboxProgressEl.classList.add('hidden');
            }
          } else {
            inboxProgressEl.classList.add('hidden');
          }
        } catch(e) {
          inboxProgressEl.classList.add('hidden');
        }
        setTimeout(pollInboxProgress, 2000);
      }
      
      // Start polling
      pollInboxProgress();

    })();

  
  