<div dir="rtl">

# אירוע אבטחה — credential חשוף

## כללי טיפול

- ערך הסוד לא שוחזר במסמך זה ולא הועתק לארטיפקט אחר.
- הסוד לא שימש לבדיקת חיבור או לכל פעולה חיצונית.
- נדרש ביטול או סבב החלפה אצל הספק.
- אין טענה שהסוד בוטל או הוחלף.

## היקף החשיפה

הסריקה המצונזרת זיהתה שני קבצים בעלי דפוס API credential בביטחון גבוה:

1. `C:\Avihusitton\‏‏מסמך טקסט חדש.txt`
2. `C:\Avihusitton\avihu-knowledge\clinical_app.py`

לא זוהה מאגר Git בשורש `C:\Avihusitton`, ושני הקבצים אינם tracked במאגרים שזוהו עבורם. לקובץ הראשון לא נמצאו הפניות מהקוד. לא נמצאו קובצי private key או connection strings עם credentials מוטמעים בסריקה המצונזרת.

שמות של קובצי `.env` ו־`.env.example` נצפו במספר פרויקטים, אך תוכנם לא הודפס ולא סווג אוטומטית כחשיפה. בתוך `clinical_ai`, קובצי `.env` מכוסים על ידי `.gitignore`.

## הכלה מקומית

לא הועתק ערך סודי, לא נוסף reference חדש ולא הוכנס סוד למאגר `clinical_ai`. שני המקורות בעלי הביטחון הגבוה נמצאים מחוץ לשורש הכתיבה של המשימה, ולכן לא שונו או נמחקו. מחיקה בלבד גם לא תבטל credential שכבר נחשף.

```text
CREDENTIAL_ROTATION_VERIFIED: false
OWNER_ACTION_REQUIRED: true
LOCAL_CONTAINMENT_COMPLETE: false
```

## פעולה שנותרה לבעלים

1. לבטל או להחליף אצל הספק את שני ה־credentials החשודים.
2. לאחר הביטול, להסיר את הערך מקובץ הטקסט.
3. לבדוק את `avihu-knowledge/clinical_app.py` בהקשר הפרויקט שלו ולהעביר כל credential פעיל למנגנון secrets מאושר.
4. לבצע סריקה חוזרת מצונזרת ולאמת שאין עוד ערכים פעילים.

אין לבצע dictionary ingestion או Neo4j write לפני השלמת הפעולות החיצוניות ואימותן.

## חריגת סיכון זמנית שאושרה על ידי הבעלים

ב־28/07/2026 בשעה `19:52:44+03:00` אישר בעל הפרויקט להמשיך במסלול
המילון ו־Neo4j staging למרות ששני ה־literals של OpenRouter עדיין קיימים.
הבעלים דיווח שהמפתח מוגבל להוצאה כוללת של 45 דולר, והתחייב להעבירו בהמשך
לקובץ סוד ולהחליף את ההפניה.

החריגה מחליפה את הוראת העצירה המקומית של אירוע זה בלבד. היא אינה מהווה
ראיה לביטול או להחלפת המפתח, אינה מתירה להדפיס או להשתמש בו, ואינה מרחיבה
הרשאה ל־production, לתעבורה קלינית חיה או למידע מטופלים.

```text
OWNER_TEMPORARY_RISK_ACCEPTANCE: true
OWNER_REPORTED_TOTAL_SPEND_LIMIT_USD: 45
CREDENTIAL_USE_AUTHORIZED: false
CREDENTIAL_ROTATION_VERIFIED: false
LOCAL_CONTAINMENT_COMPLETE: false
OWNER_FOLLOW_UP_REQUIRED: true
EXCEPTION_SCOPE: DICTIONARY_AND_NEO4J_STAGING_PATH_ONLY
```

</div>
