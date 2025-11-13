from enum import StrEnum


class FormattingPrompts(StrEnum):
    SENTENCE_CASE_CHECK_STRING = """
    You are a sentence case validator.
    Your task is to check if given title is written in sentence case, which is the only correct text formatting. 
    All other types of formatting - camel case, title case, full lowercase, full uppercase etc. - are not acceptable.

    DEFINITTION OF SENTENCE CASE
        In English, the standard is to capitalize the first letter of a sentence. 
        All other letters should be in lowercase with a few exceptions, such as proper nouns (e.g., “Texas”), abbreviations (e.g., “Dr.”), and acronyms (e.g., “NATO”). 
        Because this style follows the same capitalization rules as sentences, it is called "sentence case".

    CAPITALIZATION RULES TO ENFORCE
    1. Acronyms and abbreviations (e.g., AI, NATO, ISO, IBM) must always be fully capitalized wherever they appear.
    2. Every string must begin with a capital letter.
    3. All other words must be lowercase, **unless** they are:
        - Proper nouns (e.g., French Revolution, John, Microsoft, Union européenne),
        - Brand names (e.g., YouTube, Airbnb, Spotify, BMW, H&M, LVMH),
        - Roman numerals (e.g. I, II, IV, XX),
        - Initialisms and any other words which are normally capitalized (FBI, EU, GDP, TVA etc.)

    SPECIAL CASE — FULL LOWERCASE:
    If the entire sentence is written in lowercase, reply with:
    "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."

    FORMAT:
    Return a Python dictionary with the following fields:
    - "correct_case": True or False
    - "explanation": A brief explanation:
        - If correct: Confirm the capitalization is correct.
        - If incorrect: Explain what’s wrong.
        - If every word is lowercase, return "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout.".

    EVALUATE THIS TITLE:
    {text}
    """

    CASE_CHECK_STRING_ASSISTANT_US = """
    Refer to the following examples.

    Example 1 — Correct:
    Input: "The European Commission released its report on AI ethics in 2025"
    Output:
    {{
        "correct_case": true,
        "explanation": "The text is properly capitalized."
    }}

    Example 2 — Incorrect (All Lowercase):
    Input: "the european commission released its report on ai ethics in 2025"
    Output:
    {{
        "correct_case": false,
        "explanation": "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."
    }}

    Example 3 — Partially Incorrect:
    Input: "the European commission released its report on AI ethics in 2025."
    Output:
    {{
        "correct_case": false,
        "explanation": "The text has capitalization issues:\n- 'the' should be capitalized at the beginning of the sentence.\n- 'commission' should be capitalized as part of 'European Commission'.\nCorrect sentence: 'The European Commission released its report on AI ethics in 2025.'"
    }}
    """

    CASE_CHECK_STRING_ASSISTANT_FR = """
    Refer to the following examples.

    Example 1 — Correct:
    Input: "La Commission européenne a publié son rapport sur l'éthique de l'IA en 2025"
    Output:
    {
        "correct_case": true,
        "explanation": "The text is properly capitalized."
    }

    Example 2 — Incorrect (All Lowercase):
    Input: "la commission européenne a publié son rapport sur l'éthique de l'ia en 2025"
    Output:
    {
        "correct_case": false,
        "explanation": "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."
    }

    Example 3 — Partially Incorrect:
    Input: "la Commission européenne a publié son rapport sur l'éthique de l'IA en 2025."
    Output:
    {
        "correct_case": false,
        "explanation": "The text has capitalization issues:\n- 'la' should be capitalized at the beginning of the sentence.\nCorrect sentence: 'La Commission européenne a publié son rapport sur l'éthique de l'IA en 2025.'"
    }
    """

    SENTENCE_CASE_CHECK_JSON = """
    You will be provided with a JSON that contains a set of strings.
    Your task is to determine whether each string follows **sentence case capitalization rules**, including special treatment for acronyms, proper nouns, and headings.

    DEFINITTION OF SENTENCE CASE
        In English, the standard is to capitalize the first letter of a sentence. 
        All other letters should be in lowercase with a few exceptions, such as proper nouns (e.g., “Texas”), abbreviations (e.g., “Dr.”), and acronyms (e.g., “NATO”). 
        Because this style follows the same capitalization rules as sentences, it is called "sentence case".

    CAPITALIZATION RULES TO ENFORCE
    1. Acronyms and abbreviations (e.g., AI, NATO, ISO, IBM) must always be fully capitalized wherever they appear.
    2. Every string must begin with a capital letter.
    3. All other words must be lowercase, **unless** they are:
        - Proper nouns (e.g., French Revolution, John, Microsoft, Union européenne),
        - Brand names (e.g., YouTube, Airbnb, Spotify, BMW, H&M, LVMH),
        - Roman numerals (e.g. I, II, IV, XX),
        - Initialisms and any other words which are normally capitalized (FBI, EU, GDP, TVA etc.)

    EVALUATION GUIDELINES
        - Apply these rules to **every string**. There is no distinction between "titles", "labels", or "sentences"—they are all evaluated as regular sentence-case strings.
        - Evaluate only the text content inside fields such as "long" or "short". Ignore any schema, field names, or syntax structure.
        - Do not hallucinate errors. If capitalization is correct under the rules above, mark it as valid.

    SPECIAL CASE – FULL LOWERCASE TEXT
    If the entire text content (or the overwhelming majority of it) is written in lowercase — including acronyms, proper nouns, and sentence beginnings — do not list each individual issue. Instead, return this explanation:
    "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."

    OUTPUT FORMAT
    Return a dictionary with two fields:
    - "correct_case": Boolean — True if all capitalization is correct, otherwise False.
    - "explanation": A string
        - If correct: a short confirmation that capitalization is correct.
        - If incorrect: a list of specific issues for each violating string.
        - If lowercase: use the standard lowercase warning message above.

    Check the following data structure, focusing ONLY on the actual text content within string fields:
    {text}
    """

    CASE_CHECK_JSON_ASSISTANT_US = """
    Refer to the following examples to understand how to analyze capitalization in structured data.

    Example 1 (correctly formatted):
    Input: [H2HeaderSchema(long='Exploring how the French Revolution shaped modern American political thought', short='Political influence'), H2HeaderSchema(long='The French Revolution influence on democracy', short='Democratic impact')]
    Output:
    {{
        "correct_case": true,
        "explanation": "All text content is properly capitalized. Sentence beginnings start with capital letters, and proper nouns like 'French Revolution' and 'American' are correctly capitalized."
    }}

    Example 2 (lowercase):
    Input: [H2HeaderSchema(long='exploring how the french revolution shaped modern american political thought', short='Political influence')]
    Output:
    {{
        "correct_case": false,
        "explanation": "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."
    }}

    Example 3 (incorrectly formatted):
    Input: [H2HeaderSchema(long='How the french revolution impacted american law', short='legal implications'), H2HeaderSchema(long='The role of french citizens in the revolution', short='Citizen impact')]
    Output:
    {{
        "correct_case": false,
        "explanation": "1. In 'How the french revolution impacted american law':
        - 'french' should be capitalized as a proper noun: 'French'
        - 'american' should be capitalized as a proper noun: 'American'
        Correct form: 'How the French Revolution impacted American law'

        2. In 'legal implications':
        - 'legal' should be capitalized as it starts the phrase: 'Legal'
        Correct form: 'Legal implications'

        3. In 'The role of french citizens in the revolution':
        - 'french' should be capitalized as a proper noun: 'French'
        Correct form: 'The role of French citizens in the revolution'"
    }}
    """

    CASE_CHECK_JSON_ASSISTANT_FR = """
    Refer to the following examples to understand how to analyze capitalization in structured data.

    Example 1 (correctly formatted):
    Input: [H2HeaderSchema(long='La Révolution française a profondément influencé la pensée politique moderne', short='Impact politique'), H2HeaderSchema(long='Les idées des Lumières et leur rôle dans les réformes', short='Rôle des Lumières')]
    Output:
    {
        "correct_case": true,
        "explanation": "All text content is properly capitalized. Sentence beginnings start with capital letters, and proper nouns like 'Révolution française' and 'Lumières' are correctly capitalized."
    }

    Example 2 (lowercase):
    Input: [H2HeaderSchema(long='la révolution française a profondément influencé la pensée politique moderne', short='impact politique')]
    Output:
    {
        "correct_case": false,
        "explanation": "The entire text appears to be written in lowercase, including sentence beginnings, acronyms, and proper nouns. It needs full capitalization corrections throughout."
    }

    Example 3 (incorrectly formatted):
    Input: [H2HeaderSchema(long='Comment la révolution française a changé la société', short='influence sociale'), H2HeaderSchema(long='Le rôle des philosophes des lumières dans le changement', short='rôle des lumières')]
    Output:
    {
        "correct_case": false,
        "explanation": "1. In 'Comment la révolution française a changé la société':
        - 'révolution française' should be capitalized as a proper noun: 'Révolution française'
        Correct form: 'Comment la Révolution française a changé la société'

        2. In 'influence sociale':
        - 'influence' should be capitalized as it starts the phrase: 'Influence'
        Correct form: 'Influence sociale'

        3. In 'Le rôle des philosophes des lumières dans le changement':
        - 'lumières' should be capitalized as a proper noun referring to a historical movement: 'Lumières'
        Correct form: 'Le rôle des philosophes des Lumières dans le changement'"
    }
    """

    REPLACE_CAMEL_CASE_LIST_TEMPLATE = """
    You are a helpful text formatting assistant.

    You will be provided with either:
    - A list of plain strings, or
    - A structured input (e.g., list of dictionaries with fields like 'title', 'description', 'long', 'short' etc.)

    Your task is to rewrite **each string value** in sentence case based on the grammar rules of the language specified.
    Language: <<{language}>>

    Sentence case rules to reinforce:
    1. All **acronyms** (e.g., AI, ISO, IEEE) must always be **fully capitalized** wherever they appear.
    2. Every **sentence** must begin with a capital letter. This includes sentences that follow periods (.), exclamation points (!), or question marks (?).
    3. Use **sentence case**: only the **first word** of each sentence should be capitalized, unless another word is:
        - a **proper noun** (e.g., French Revolution, Dubai, European Commission),
        - a **brand name** (e.g., Microsoft, YouTube),
        - or an **acronym** (e.g., AI, NATO).
    4. **Short phrases** (e.g., section titles or labels such as 'Political influence') are acceptable if:
        - Only the **first word** is capitalized,
        - The phrase does **not attempt to mimic full sentence structure** (i.e., no ending punctuation, no verb clauses).

    Rules:
    - Maintain the original input structure (list or schema), including keys and nested formats.
    - Modify only the text values — **do not alter keys, data structure, or field order**.
    - Do not touch HTML tags or other non-text markup within the values — only change visible text.
    - Wrap every list item (plain string or object field) in double quotes as applicable.

    If provided, refer to the explanations what's wrong with given text formatting:
    {explanation}

    Content:
    {content}

    Output must only include the formatted content. Do not add extra explanations, labels, or assign the output to a variable.
    """

    REPLACE_CAMEL_CASE_LIST_ASSISTANT = """
    Refer to the following examples for how to apply sentence case formatting.

    Example 1 (English — list of strings)
    Input: ["types of car tires", "Selection and Purchase of Tires", "comprehensive SEO strategies for Business Growth"]
    Output: ["Types of car tires", "Selection and purchase of tires", "Comprehensive SEO strategies for business growth"]

    Example 2 (English — list of schemas)
    Input:
    [
        {{ "title": "company annual report", "description": "overview of fiscal year 2025 results" }},
        {{ "title": "market analysis and Forecast", "description": "trends in tech industry" }},
        {{ "title": "AI IN MODERN HEALTHCARE", "description": "applications of artificial intelligence" }}
    ]
    Output:
    [
        {{ "title": "Company annual report", "description": "Overview of fiscal year 2025 results" }},
        {{ "title": "Market analysis and forecast", "description": "Trends in tech industry" }},
        {{ "title": "AI in modern healthcare", "description": "Applications of artificial intelligence" }}
    ]

    Example 3 (French — list of strings)
    Input: ["UTILISATION DE L’INTELLIGENCE ARTIFICIELLE EN MARKETING", "Facteurs Clés De Succès Dans Les Startups", "Impact Du Télétravail Sur La Productivité"]
    Output: ["Utilisation de l’intelligence artificielle en marketing", "Facteurs clés de succès dans les startups", "Impact du télétravail sur la productivité"]

    Example 4 (French — list of schemas)
    Input:
    [
        {{ "title": "CHANGEMENTS CLIMATIQUES ET AGRICULTURE", "description": "Conséquences Sur Les Récoltes En Europe" }},
        {{ "title": "Technologies Vertes En Plein Essor", "description": "Solutions Innovantes Pour L’environnement" }},
        {{ "title": "Gestion Des Déchets Urbains", "description": "Modèles De Traitement Durable" }}
    ]
    Output:
    [
        {{ "title": "Changements climatiques et agriculture", "description": "Conséquences sur les récoltes en Europe" }},
        {{ "title": "Technologies vertes en plein essor", "description": "Solutions innovantes pour l’environnement" }},
        {{ "title": "Gestion des déchets urbains", "description": "Modèles de traitement durable" }}
    ]
    """

    REPLACE_CAMEL_CASE_TEMPLATE = """
    You are a helpful text formatting assistant.
    Rewrite input text in sentence case. The language of text is <<{language}>>.

    Sentence case means:
    1. ALWAYS capitalize the first letter of each sentence
    2. Keep all other words lowercase EXCEPT for:
    - Proper nouns (names of specific people, places, brands, companies)
    - Acronyms (like NASA, BBC, RAM, CPU, AI)
    - Initialisms and abbreviations (like FBI, USA, UK)
    - Roman numerals (like I, II, IV, XX)
    - Brand and product names (like Razer, Logitech, Corsair, macOS, iOS)
    - Technical terms that are conventionally capitalized (like RGB)
    and other words and collocations which are normally capitalized or written in upper case.

    Important rules:
    - After periods (.), question marks (?), exclamation points (!), and colons (:) that end a sentence, the next word MUST start with a capital letter
    - Check every sentence carefully to ensure its first word begins with a capital letter
    - Maintain the original structure and meaning of the input
    - Don't add quotes, return simply text
    - You format text only, you are not allowed to modify tags including HTML ones

    Content:
    {content}

    Output must be simply a piece of formatted content, don't add any extra text and don't assign it to any variables.
    If content is initially correctly formatted in sentence case, skip it and return content as it is. 
    """

    REPLACE_CAMEL_CASE_ASSISTANT = """
    Refer to the following examples:

    Input: types of car tires
    Output: Types of car tires

    Input: Elizabeth II a Gouverné la Grande-Bretagne aux XXe et XXIe Siècles.
    Output: Elizabeth II a gouverné la Grande-Bretagne aux XXe et XXIe siècles.

    Input: Information About Nasa
    Output: Information about NASA

    Input: learn to code In Python
    Output: Learn to code in Python

    Input: It Is A Cool Day
    Output: It is a cool day

    Input: hello. my name is john. i live in new york.
    Output: Hello. My name is John. I live in New York.

    Input: what is ai? artificial intelligence is changing the world
    Output: What is AI? Artificial intelligence is changing the world
    """

    FIX_CASE_H2_CONTENT_TEMPLATE = """
    You are a helpful text formatting assistant.
    Apply the case corrections to the input text based on the explanation provided. The language of text is <<{language}>>.

    Important rules:
    - Follow the capitalization corrections exactly as specified in the explanation
    - Maintain the original structure and meaning of the input
    - Don't add quotes, return simply the corrected text
    - You format text only, you are not allowed to modify tags including HTML ones

    Original content:
    {content}

    Issues found in the text regarding its case formatting:
    {explanation}

    Output must be simply the piece of formatted content with all capitalization issues fixed according to the explanation. Don't add any extra text and don't assign it to any variables.
    """

    MINDMAP_FORMATTING_ASSISTANT = """
    ### Examples

    Language - US
    Input:
    L1. mastering remote work: tips for 2025 professionals  
    L2. setting up an ergonomic home office  
    L3. choosing between ikea and herman miller furniture  
    L3. optimizing lighting with philips hue smart bulbs  
    L2. streamlining daily workflows  
    L3. using notion & trello for task management  
    L3. automating repetitive tasks with zapier & make  
    L2. maintaining work–life balance  
    L3. scheduling focus blocks with the pomodoro technique  
    L3. incorporating outdoor breaks and short workouts  

    Output:
    L1. Mastering remote work: Tips for 2025 professionals  
    L2. Setting up an ergonomic home office  
    L3. Choosing between IKEA and Herman Miller furniture  
    L3. Optimizing lighting with Philips Hue smart bulbs  
    L2. Streamlining daily workflows  
    L3. Using Notion & Trello for task management  
    L3. Automating repetitive tasks with Zapier & Make  
    L2. Maintaining work–life balance  
    L3. Scheduling focus blocks with the Pomodoro technique  
    L3. Incorporating outdoor breaks and short workouts  

    Language - FR
    Input:
    L1. découvrir la gastronomie lyonnaise en 2025  
    L2. goûter les spécialités locales au marché des halles de lyon  
    L3. réserver un cours de cuisine avec l'institut paul bocuse  
    L2. explorer les vignobles du beaujolais en train sncf  
    L3. organiser une dégustation au château de pizay  

    Output:
    L1. Découvrir la gastronomie lyonnaise en 2025  
    L2. Goûter les spécialités locales au Marché des Halles de Lyon  
    L3. Réserver un cours de cuisine avec l'Institut Paul Bocuse  
    L2. Explorer les vignobles du Beaujolais en train SNCF  
    L3. Organiser une dégustation au Château de Pizay  
    """

    REPHRASE_TEMPLATE = """
    Rewrite the provided HTML-formatted text while preserving its original meaning and
    maintaining all critical points. 
    Use a concise and clear tone of voice, ensuring the new version conveys the same message and style 
    as the original text without altering its intent or omitting any significant details. 
    Maintain all existing HTML tags 
    and their structure in the rewritten version — the output should match the formatting of the input exactly, 
    with only the phrasing of the text changed.
    Text to rewrite (HTML included): 

    {input_text}
    """
