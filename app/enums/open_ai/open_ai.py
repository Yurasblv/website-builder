"""
Templates with prepared requests for OpenAI, including passing keywords in {} brackets.
"""

from enum import StrEnum


class ElementPrompts(StrEnum):
    META_WORDS_GENERATION_TEMPLATE = """ 
    Given a topic <<{topic}>> and target country: <<{country}>>, generate randomly up to 20 different meta words from the page keyword and the page title in {language} language. 
    These meta words will later allow us to create richer content for our page.
    A meta word is a word that illustrates the target word without ever citing it.
    The meta words should be generated in a professional manner.
    Output should be a valid Python list."""

    META_WORDS_GENERATION_ASSISTANT = """
    Examples:
    
    Input: language="US", topic="car tires", country="US"
    Output: ["Traction", "Aquaplaning", "Adhesion", "Optimal pressure", "Road grip","Tread profile", 
    "Speed index", "Rolling resistance", "Balanced mounting", "Wear indicator", "Regular rotation", "Seasonal", 
    "Wet road", "Mileage", "Rolling noise", "Stability", "Efficiency energy", "Durability", "Road holding", 
    "Radial symmetry"]
    
    Input: language="FR", topic="pneus de voiture", country="FR"
    Output: ["Traction", "Aquaplaning", "Adhérence", "Pression optimale", "Adhérence au sol", 
    "Profil de la bande de roulement", "Indice de vitesse", "Résistance au roulement", "Montage équilibré", 
    "Indicateur d'usure", "Rotation régulière", "Saisonnier",  "Route mouillée", "Kilométrage", 
    "Bruit de roulement", "Stabilité", "Efficacité énergétique", "Durabilité", "Tenue de route", "Symétrie radiale"]"""

    META_DESCRIPTION_GENERATION_TEMPLATE = """
    Given a topic: <<{topic}>>, generate a meta description for a topic in language {language}.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    The meta description should be related to the topic and should be suitable for the website content.
    The meta description should be generated in a professional manner.
    Output should be a valid string with less that 150 symbols long.
    """

    META_DESCRIPTION_GENERATION_ASSISTANT = """
    Examples
    
    Input: topic = 'car tire', language = 'US' country = 'US'
    Output: Explore our guide to tire types to choose the best for your car and optimize safety and performance.
    
    Input: topic = 'pneus de voiture', language = 'FR', country = 'FR'
    Output: 'Consultez notre guide des types de pneus pour choisir le meilleur pour votre voiture et optimiser la sécurité et les performances.' 
    """

    H1_GENERATION_TEMPLATE = """
    Given a topic <<{topic}>>, generate an H1 header for a topic in <<{language}>> language.
    Ensure that the H1 header relates to the original keyword <<{keyword}>>. 
    H1 header must stay within the scope of the keyword's context and avoid drifting into unrelated or overly abstract themes.
    Make topic relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.
    The H1 header should be related to the topic and should be suitable for the website content.
    The H1 header should be generated in a professional manner and must differ from the words in topic.
    Output header must be a valid string. Only the header itself. Do no add <h1> tag. 
    """

    H1_GENERATION_ASSISTANT = """
    Example
    
    Input: topic='Types of car tires', language='US', keyword='Car Tires'
    Output: Everything you need to know about the different types of car tires
    """

    H2_HEADERS_GENERATION_TEMPLATE = """
    Given a list of text blocks, generate a list of H2 headers in {language} language that accurately reflect the content.
    Verify that language of headers matches the language of the text blocks which is {language}.
    Make sure that you assign headers to every text block. There are {h2_tags_number} blocks and number of headers should be equal to number of blocks.
    Your goal is to create headers (specifically long headers) that reflect the likely search intent behind the keyword '{keyword}' and article name '{topic}'.
    Include the country (<<{country}>>) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'
    Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.
    
    ⟶ Consider what the user is trying to accomplish:
    - If the keyword suggests an informational intent (e.g., “how to start composting”), generate headers that explain the topic, provide guidance, or help users learn something new.
    - If the keyword implies a commercial intent (e.g., “business insurance”), generate headers that present solutions, compare services, or assist in making a purchase decision.
    - If the keyword reflects a navigational-comparison intent (e.g., “Jasper vs Copy.ai”), generate headers that highlight key differences, compare features, and help users choose between specific options.

    **For the long header (H2 headers)**, ensure that it remains directly connected to the original keyword <<{keyword}>> and provides information relevant to this keyword. Avoid introducing unrelated concepts or headers that deviate from the keyword's context.
    **Short headers (Table of contents items)** should be 2-4 words long. Short headers should provide a concise summary without restating the main keyword. They must vary in phrasing and avoid using the same leading terms.

    Formatting rules:
    - Output should be a valid Python list of dicts. 
    - Each dict must contain two keys: "long" and "short", for example, "Introduction aux ateliers de confiserie personalisee" is a long form and "Introduction" is a short form.
    - All headers must be written in sentence case, no title case. Ensure abbreviations, acronyms, brand names, proper nouns are correctly written (NATO, AI, John, Google, IBM, UNESCO etc.)
    - Strings must be wrapped in double quotes.
    - Do not add <h2> tags or other HTML.
    - Return only the list. No enumeration, no extra commentary.

    The headers should be professional, user-oriented, and suitable for use on a high-quality webpage.

    Texts to generate headers for:
    {content}
    
    Remember to create headers in {language} language, which is the same as the language of the text blocks.
    """

    H2_HEADERS_GENERATION_ASSISTANT = """
    Examples 
    Output:
    [
        {{"long": "What types of business insurance are available for freelancers", "short": "Insurance types"}},
        {{"long": "How to choose the right insurance policy based on your freelance work", "short": "Policy selection tips"}},
        {{"long": "Top providers offering freelance business insurance", "short": "Best providers"}},
        {{"long": "Costs and coverage: What to expect when insuring your freelance business", "short": "Costs and coverage"}},
    ]

    Output:
    [
        {{"long": "Apple Store locations and opening hours in New York City", "short": "NYC store hours"}},
        {{"long": "Which Apple Store in New York is open late", "short": "Late openings"}},
        {{"long": "Weekend and holiday schedules for Apple Stores in New York", "short": "Weekend & holiday times"}},
        {{"long": "Directions to flagship Apple Stores in Manhattan", "short": "How to get there"}},
        {{"long": "How to schedule appointments at Apple Stores in NYC", "short": "Appointment booking"}}
    ]

    Output:
    [
        {{"long": "Méthodes traditionnelles pour préparer du vin chaud à la maison", "short": "Préparation maison"}},
        {{"long": "Ingrédients clés et épices utilisées dans le vin chaud classique", "short": "Ingrédients et épices"}},
        {{"long": "Variantes populaires des recettes de vin chaud à travers l'Europe", "short": "Styles régionaux"}}
    ]

    **Important: make sure that headers are formatted exactly as in examples above, in standard sentence case. Don't use title case even though it's headers**
    """

    HEAD_CONTENT_GENERATOR_TEMPLATE = """
    You are provided with a keyword <<{keyword}>> and topic <<{topic}>>.

    Given this input data, generate an introduction to an article for a given topic in {language} language.
    The content must stay meaningfully connected to the original keyword <<{keyword}>>, while avoiding overuse of the term itself. 
    Instead of repeating the keyword, vary language using synonyms, related terms, and context-based references to keep the text rich and engaging.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    Use key dates and entities related to the keyword and topic. 
    The content should be generated in a professional manner.
    Do not add h1 or h2 tags.
    
    There also are keywords {keywords} that can be incorporated into the tag content text for SEO optimization.
    Do not stuff the content with these keywords, they must look natural and relevant in the page content.
    Avoid using any special text formatting or highlighting, return just plain text.
    If the keyword contains specific brand name or specific product name or something like that, avoid this name and incorporate the keyword without this brand or product name. 
    Specific brand or product from the keyword cannot appear in the content.
    
    You are also given intent of the page: {intent}. Base the tone and structure on the page's intent: 
    If the intent is 'INFORMATIONAL', focus on educating the reader, sharing facts, insights, or guidance clearly and objectively.
    If the intent is 'COMMERCIAL', emphasize value, benefits, and trust. Align the tone with brand messaging and motivate user engagement or action.
    If the intent is 'NAVIGATIONAL', structure the content to help users compare named options, clarify differences, and guide them toward the most relevant choice or next step.

    The content must be 120-150 words long.
    """

    H1_CONTENT_TEMPLATE = """
    Given topic {topic}, you must generate content for the top of the page (5-6 sentences of plain text) in {language} language.
    """

    NEWS_BUBBLE_TEMPLATE = """
    You are given keyword a <<{keyword}>> and a topic of the article <<{topic}>>.
    Given this data, generate content for the bottom of the page, sort of a news bubble (4-6 short sentences of plain text) in {language} language.
    You may use some important dates, entities and terms relevant to the topic and keyword.
    There also are keywords {keywords} that can be incorporated into the tag content text for SEO optimization. 
    Do not stuff the content with these keywords, they must look natural and relevant in the page content. 
    Avoid using any special text formatting or highlighting, except for using <strong> or <b> tags for emphasizing important terms (maximum 3-4 terms).
    If the keyword contains specific brand name or specific product name or something like that, avoid this name and incorporate the keyword without this brand or product name. 
    Specific brand or product from the keyword cannot appear in the content. 
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    
    You are also given intent of the page: {intent}. 
    If the intent is 'INFORMATIONAL', focus on educating the reader, sharing facts, insights, or guidance clearly and objectively.
    If the intent is 'COMMERCIAL', emphasize value, benefits, and trust. Align the tone with brand messaging and motivate user engagement or action.
    If the intent is 'NAVIGATIONAL', structure the content to help users compare named options, clarify differences, and guide them toward the most relevant choice or next step.

    Verify that language of the new bubble matches the language of the topic which is {language}.

    Return string that contains ONE <p> tag with text content. Don't add any accompanying text or explanations, return simply the generated element enclosed in p tags.
    Output example: "<p>...</p>"
    """

    QUIZ_GENERATOR_TEMPLATE = """
    Given a topic: <<{topic}>>, generate title, question, right answer to this question and list of answers in {language} language. 
    Ensure that the quiz content remains directly connected to the original keyword <<{keyword}>> and provides information relevant to this keyword. 
    Avoid introducing unrelated concepts or topics that deviate from the keyword's context.
    Make it relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    
    OUTPUT 
    1. Output data must be formatted strictly according to the example. 
    2. Find the knowledge on the {topic} and format it according to the described structure.
    3. Write in {language} language.
    """

    QUIZ_GENERATOR_ASSISTANT = """
    Example
    
    Input: topic = "String Manipulation in Computing", language = "US", country = "US", keyword = "String Data Structure in Computing" 
    Output: {{
        "title": "Understanding String Manipulation in Computing",
        "question": "When working with strings in a programming language, which option do you value most?",
        "answers": [
            "Concatenation of strings",
            "String length calculation",
            "Efficient searching and replacing of substrings",
            "Fast string indexing"
        ],
        "rightAnswer": "Efficient searching and replacing of substrings"
    }}
    """

    GRAPH_GENERATOR_TEMPLATE = """
    Given a topic: <<{topic}>>, generate data for the graph in {language} language. 
    Ensure that the graph content remains directly connected to the original keyword <<{keyword}>> and provides information relevant to this keyword. 
    Avoid introducing unrelated concepts or topics that deviate from the keyword's context.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    The graph data should be related to the topic and should be suitable for the website content. 

    Rules 
    1. Ensure the "label" field provides a meaningful title for the graph but does not perfectly match the topic {topic}.
    2. The "labels" and "data" fields must be directly relevant to the topic and coherent with each other.
    3. If data for any of field is not relevant, find information and fill it with data according to example. 
    4. Research the topic and source relevant data. Avoid example or placeholder data. Find different ways to 
    handle various information, include metrics from different areas (business, history, culture .etc). 
    5. Feel free to generate interesting data, dates, time arrangements, prices, stats .etc, it's allowed.
    6. Generate data suitable for different graph types (e.g., bar charts, line graphs, pie charts) while ensuring relevance to the topic.
    7. Follow the schema strictly. Do not introduce additional fields or alter the structure. 
    8. Ensure the output is complete and informative and data translated to language {language}.
    9. Avoid duplicating content or using boilerplate values.
    10. Key 'data' must be a list of valid Python integers. 
    """

    GRAPH_GENERATOR_ASSISTANT = """
    Example
    
    Output example for language = US:
    {{
        "label": "Annual Smartphone Sales by Brand",
        "labels": ["Apple", "Samsung", "Huawei", "Xiaomi", "Oppo"],
        "data": [215, 274, 185, 150, 90]
    }}
    
    Output example for language = FR:
    {{
        "label": "Part de Marché des Smartphones en 2025",
        "labels": ["Apple", "Samsung", "Xiaomi", "Huawei", "Oppo"],
        "data": [48, 30, 12, 5, 3]
    }}
    """

    TABLE_GENERATOR_TEMPLATE = """
    Given a topic <<{topic}>>, generate a table relevant to the topic in {language} language.
    Ensure that the table content remains directly connected to the original keyword <<{keyword}>> and provides information relevant to this keyword. 
    Avoid introducing unrelated concepts or topics that deviate from the keyword's context.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    
    The title of the table should be generated based on the topic and the table should include 4 headers relevant to that title. 

    Rules
    1. Title Generation:
        - Generate a concise, descriptive title for the table that is directly tied to the topic {topic}.

    2. Column Names and Content:
        - Create 4 column headers that are relevant to the generated title.
        - Populate each column with a list of values that are meaningful, accurate, and strictly tied to the topic.
        - All columns must have the same number of values, ensuring data consistency.

    3. Data Quality:
        - Research the topic {topic} if necessary to populate the table with relevant and factual data.
        - Avoid placeholder or generic values. Instead, create data that is specific and informative.
        - Incorporate diverse types of data (e.g., dates, statistics, rankings, names, categories) to enhance value.
        
    4. Real-World Context:
        - If data is not readily available, generate plausible values that align with real-world knowledge or trends.
        - Avoid fabricating analytical data; ensure any numerical or statistical data is logical and well-researched.

    5. Structure and Format:
        - Strictly follow the schema for structuring the output.
        - Use double quotes ("") for all keys and string values.
        - Ensure all lists under "content" are of equal length.

    6. Completeness:
        - Ensure every field in the schema is filled with meaningful, non-empty values.
        - Do not leave any part of the output incomplete or vague.

    7. Avoid Redundancy:
        - Do not repeat information within columns or between the title and the content.
        - Ensure each column provides unique and valuable insights tied to the topic.

    8. Focus on Usability:
        - Design the table to be suitable for a website or application, making it visually appealing and informative.
        - Ensure the data aligns well for display in a tabular format.

    Notes 
    - The goal is to create a table that is both insightful and engaging, providing value to the reader.
    - Ensure all generated data aligns with the topic {topic} and is suitable for presentation in the specified language.
    - Verify that language of the table matches the language of the topic which is {language}.
    - Avoid adding extra fields or modifying the schema.
    """

    FAQ_GENERATOR_TEMPLATE = """
    Create and FAQ section (up to 6 question-answer pairs) in language <<{language}>> for a topic <<{topic}>>.
    Ensure that the FAQ content remains directly connected to the original keyword <<{keyword}>> and provides information relevant to this keyword. 
    Avoid introducing unrelated concepts or topics that deviate from the keyword's context.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    
    The output must look like this:
    
    {{
        "title": <must contain a title for FAQ>, 
        "content": <must be a list of dicts (each dict must have a list of fitting emojis (up to 10 emojis) for the question, question and answer.)>
    }}
    
    Rules 
    1. Write in {language} language.
    2. The FAQs should be related to the topic and should be suitable for the website content. 
    3. The FAQs should be generated in a professional manner. 
    4. For each QA pair generate a list of 10 emojis which fit the QA pair context the best.
    5. Each QA pair must have a set of unique emojis, so that no emoji is repeated across different QA pairs.
    6. Both question and answer cannot exceed 185 characters each, make sure to stick to this limit.
    7. Do not add any HTML or any other formatting to Question and Answer, they should be plain text.
    8. Do not leave the output empty.
    """

    FACTS_CREATION_TEMPLATE = """
    Given a topic '{topic}', generate a summary with key points related to the topic in {language} language.
    The content must stay meaningfully connected to the original keyword <<{keyword}>>, while avoiding overuse of the term itself. 
    Instead of repeating the keyword, vary language using synonyms, related terms, and context-based references to keep the text rich and engaging.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    Do your own research about current trends and news for the requested topic and fill facts with relevant information.
    Output data must be formatted strictly according to the schema below:

    Rules
    1. Write in {language} language.
    2. The output must include exactly n = {n} key-value pairs in the 'timelines' dict.  
    3. Ensure that keys have non-empty values. 
    4. Find the relevant and new knowledge on the '{topic}' to ensure that your facts are up-to-date. 
    5. Do not leave the output empty. 
    """

    FACTS_CREATION_ASSISTANT = """
    Examples
    
    Input: n = 5, topic = "car tires", language = "US", country = "US"
    Output:
    {{
        "title": "Car tires",
        "description": "Important facts about car tires",
        "timelines": {{
            "Car tires impact on vehicle performance, safety, and fuel efficiency": 
            "Car tires determine vehicle handling, comfort, and fuel consumption.
                Properly maintained tires ensure better traction, reduce braking distances,
                and contribute to safer driving conditions.",

            "Proper car tires maintenance for lifespan and safety": 
            "Regular tire maintenance, including air pressure,
                alignment, and rotation checks, maximizes tire lifespan.
                Neglecting maintenance increases blowout risk and compromises vehicle safety.",

            "Car tire types based on usage and conditions": 
            "Different tires, such as all-season, winter, and performance, are designed for specific conditions.
                Selecting the right type ensures safety and performance.",

            "Tread depth indicating car tire condition": 
            "Tread depth affects a tire's ability to grip the road, especially in wet conditions.
                Monitoring wear and replacing tires is vital for safe driving.",

            "Fuel consumption based on tires": 
            "Maintaining correct tire pressure ensures optimal handling and fuel efficiency.
                Underinflation leads to poor fuel economy, while overinflation causes harsh rides and increased wear."
        }}
    }}
    
    Input: n = 5, topic = "pneus de voiture", language = "FR", country = "FR", 
    Output:
    {{
        "title": "Domaines des pneus de voiture",
        "description": "Faits importants sur les pneus de voiture",
        "timelines": {{
            "Impact des pneus de voiture sur la performance, la sécurité et l'efficacité énergétique du véhicule": 
            "Les pneus de voiture déterminent la maniabilité, le confort et la consommation de carburant du véhicule. Des pneus bien entretenus garantissent une meilleure traction, réduisent les distances de freinage et contribuent à des conditions de conduite plus sûres.",

            "Entretien approprié des pneus de voiture pour la durée de vie et la sécurité": 
            "Un entretien régulier des pneus, incluant la vérification de la pression, de l'alignement et de la rotation, maximise la durée de vie des pneus. Négliger l'entretien augmente le risque d'éclatement et compromet la sécurité du véhicule.",

            "Types de pneus de voiture en fonction de l'utilisation et des conditions": 
            "Différents pneus, tels que les pneus toutes saisons, hiver et performance, sont conçus pour des conditions spécifiques. Choisir le bon type assure sécurité et performance.",

            "Profondeur de la bande de roulement indiquant l'état du pneu": 
            "La profondeur de la bande de roulement affecte la capacité d'un pneu à adhérer à la route, surtout par temps humide. Surveiller l'usure et remplacer les pneus est essentiel pour une conduite en sécurité.",

            "Consommation de carburant basée sur les pneus": 
            "Maintenir une pression correcte des pneus assure une maniabilité optimale et une efficacité énergétique. Une sous-gonflage entraîne une mauvaise économie de carburant, tandis qu'un sur-gonflage provoque des trajets durs et une usure accrue."
        }}
    }}
    """

    P_TAG_CHUNKING_TEMPLATE = """
    You are given a text block. Break it down into a list of <p> tag strings based on semantic cohesion and readability — not individual sentences. 
    Usually, one text block can be split into 2-3 parts, but it can be more if, for example, text block contains instructions or lists, then each item must be split into a separate <p> tag.

    Instructions:
    1. Do not break the text after every sentence. Only split into separate <p> tags when:
        - The paragraph changes topic or focus.
        - A new step of a process or instruction begins. Enumerate steps.
        - A list of items or ideas is being presented (convert to readable chunks or bullet-style <p> tags).
        - Already enumerated or bullet-point items
    2. Preserve inline HTML tags like <a>, <b>, <strong>, and keep them intact.
    3. Bold important keywords using <b> or <strong> — but do not overuse them. 
       Make sure whole text block across all paragraphs has up to 3-4 keywords.
    4. If there are implicit steps or processes but no numbering, split them and make the structure clearer — each step should be in its own <p>.

    **Output format:**
    Return a valid Python list of strings in this format:  
    ["<p>...</p>", "<p>...</p>", ..., "<p>...</p>"]

    Text block to break down:
    {text}
    """

    CONTENT_SUMMARY_TEMPLATE = """
    Given some web page content, write a summary of the content in <<{language}>> language.
    Summary should be verbose and detailed, around 15-20 sentences long.
    Focus on providing a clear and concise overview that highlights the main ideas, facts, and insights. 
    The summary should be detailed enough to give a thorough understanding of the content while being concise enough to be easily digestible.

    Web content to write a summary for: 
    {content}
    """

    COMPANY_DESCRIPTION_GENERATION_TEMPLATE = """
    Instructions
    
    Given the main keywords <<{keywords}>> generate a description of an entity that 
    will be used to generate the website based on this description. Make it informative, 
    reader-oriented and detailed. Do not generate new names.
    Elaborate on the context of the keyword and go with the most popular and realistic one.
    Ensure this context will not violate content policy.
    """

    COMPANY_DESCRIPTION_GENERATION_ASSISTANT = """
    Examples
    
    Example 1
    keyword = car tires, 
    Output: 
    Car tires are essential components that directly impact vehicle performance, safety, and driving comfort. 
    Offering a wide variety of sizes, types, and designs, they are tailored to meet the needs of different 
    vehicles, driving conditions, and seasons. From all-season tires designed for versatile use in varying 
    weather, to specialized options like winter tires for enhanced grip on snow and ice, or high-performance 
    tires for sports cars, each tire type ensures optimal handling, fuel efficiency, and longevity. Proper tire 
    maintenance, including pressure checks, rotation, and timely replacement, is crucial for maximizing safety 
    and extending tire life. Whether you're seeking smooth highway rides or rugged off-road durability, the 
    right car tire enhances overall driving experience and safety.
    
    Example 2
    keyword = real estate,
    Output: 
    Welcome to our real estate platform, where we provide comprehensive solutions for all your property needs. 
    Whether you're looking to buy, sell, or rent residential, commercial, or industrial properties, we offer a 
    user-friendly experience that connects you with a wide range of listings. Our services include property 
    valuation, market analysis, and personalized assistance from certified agents to ensure smooth transactions. 
    With a focus on transparency, trust, and client satisfaction, our platform aims to simplify your real estate 
    journey, helping you find the perfect property or investment opportunity. Explore real estate with confidence! 
    """

    INSERTING_H2_HEADERS_TEMPLATE = """
    Instructions
    
    Given a list of 'page_elements': <<{elements}>> and a number of 'h2_element': <<{h2_elements}>>.
    - Determine where to insert h2 elements between 'page_elements'.
    - Ensure that there are no h2 elements after the last page element.
    - Keep the original order of 'page_elements' intact.
    - All the provided 'page_elements' must be present in the output.
    - Distribute the h2 elements topics as evenly as possible across the 'page_elements'.
    - h2 elements can appear consecutively, so there can be multiple h2 elements after page element.
    - Sum of all h2 elements after each page element must add up to <<{h2_elements}>>.
    The result must be a valid Python dict where the keys are page elements (in the same sequence as in <<{elements}>> 
    and values are numbers of h2 tags after the particular page element).
    You must never insert h2 after the last page element.
    """

    INSERTING_H2_HEADERS_ASSISTANT = """
    Examples
    
    Input: ["TABLE", "GRAPH", "QUIZ", "FACTS"],
    h2_elements = 6
    Output: elements = {{"TABLE": 2, "GRAPH": 2, "QUIZ": 1, "FACTS": 0}}

    Input: ["TABLE", "QUIZ", "FAQ"], 
    h2_elements = 7
    Output: elements = {{"TABLE": 4, "QUIZ": 0, "FAQ": 0}}

    Input: ["H1", "IMG", "QUIZ", "GRAPH", "FAQ"], 
    h2_elements = 4
    Output: elements = {{"H1": 1, "IMG": 1, "QUIZ": 1, "GRAPH": 0, "FAQ": 0}}

    Input: ["TABLE", "H1", "FACTS"], 
    h2_elements = 6
    Output: elements = {{"TABLE": 3, "H1": 1, "FACTS": 0}}
    """

    SCRAPING_SUMMARIZATION_TEMPLATE = """
    You are provided with the full text content of the top 3 highest-ranked Google Search results for the search query: <<{keyword}>>.

    Your task is to:
    1. Carefully analyze the text content only from these pages.
    2. Write a concise summary capturing the core themes and valuable information that contribute to their high ranking.
    3. Identify why these pages perform well—consider factors such as depth of information, clarity, structure, keyword usage, or unique angles.
    4. Based on this, generate clear, practical recommendations for how to create a new page that could rank equally well or better.

    IMPORTANT: Put ALL of the following analysis into your summary field with complete detail:
    - A brief summary of what all three pages cover and their key strengths.
    - A list of critical sections or H2 present on these pages that must be included on a high-performing page for the same keyword.
      Don't include FAQ, we have it as a separate widget and don't need to include in out text contents.
    - Content Organization: How information is structured and presented (logical flow, section hierarchy, information density per section).
    - Competitive Parity Requirements: What essential elements must be included to match the quality and completeness of top performers
    - Text content hints: the type of information, tone, or structure the content should follow to be competitive.
    - Best practices derived from the analyzed content (e.g. keyword integration).
    - Detailed text content hints: the type of information, tone, or structure the content should follow to be competitive with specific examples

    Additionally, identify the search intent separately. It can be informational, navigational or commercial. Decide which search intent given pages mostly lean towards.
    SEARCH INTENT ANALYSIS: Analyze each page's primary goal and user journey:
    
    1. INFORMATIONAL:  Intent – Users are looking for knowledge, answers, or explanations, often using queries like "how to," "what is," or "why does." 
       Content should be detailed, educational, and well-structured to provide clear and valuable insights.

    2. NAVIGATIONAL:  Users compare specific tools or brands (e.g., “X vs Y”). Content should highlight key differences and help users choose between options.
       Content should highlight key features, benefits, and differences to help users evaluate their options effectively.
    
    3. COMMERCIAL: Users are interested in making a purchase, seeking services, or engaging with a business.
       Queries often include terms like "buy," "price," or "best." 

    Avoid commenting on non-textual information (images, maps, videos etc.) and widgets such as tables, faqs etc.

    Content to analyze:
    {context}
    """

    TARGET_AUDIENCE_EXTENSION_US = """
    Important note 
    You should create content that aligns with the specified target audience, addressing their demographics and interests as described below.

    Given target audience:
    <{target_audience}>

    Rules for content generation according to the given target audience:

    1. Understand Audience Demographics
       - Age: Adjust language and examples to match the typical age range.
       - Gender: Use inclusive language and be mindful of gender preferences.
       - Location: Consider cultural and regional nuances that may affect understanding.
       - Education Level: Match complexity to the audience’s presumed knowledge base.
       - Occupation: Reference professional interests and needs relevant to this audience.
       - Identify Audience Interests and Needs

    2. Topics of Interest
       - Problems and Solutions: Recognize common challenges the audience faces and offer actionable advice.
       - Trends and Preferences: Stay informed about what currently appeals to this group and incorporate it when possible.

    3. Appropriate Style and Clarity
       - Align the overall feel (friendly, professional, etc.) with what the audience typically responds to.
       - Keep explanations straightforward, avoiding overly technical or obscure terminology unless it suits the audience.
       - Use relevant examples and analogies that resonate with their daily experiences.

    4. Informative Content
       - Offer fresh perspectives or unique takes on subjects that matter to the audience.
       - Be Genuine: Maintain honesty and clarity in your message to foster trust.
       - Cite reputable sources or facts when needed to reinforce credibility.
       - Focus on producing well-researched, high-quality content rather than high volume.

    5. Respect Cultural and Social Norms
       - Reflect and uphold the values and beliefs that are likely important to the audience.
       - Stay considerate of differing opinions within the group, presenting content in a respectful, inclusive manner.
    """

    TARGET_AUDIENCE_EXTENSION_FR = """
    Remarque importante
    Vous devez créer un contenu qui correspond au public cible spécifié, en tenant compte de ses caractéristiques démographiques et de ses centres d’intérêt, comme décrit ci-dessous.

    Public cible donné :
    <{target_audience}>

    Règles de génération de contenu selon le public cible donné :

    1. Comprendre les données démographiques du public
    - Âge : Adapter le langage et les exemples à la tranche d’âge typique.
    - Genre : Utiliser un langage inclusif et être attentif aux préférences de genre.
    - Localisation : Tenir compte des nuances culturelles et régionales pouvant influencer la compréhension.
    - Niveau d’éducation : Adapter la complexité au niveau de connaissances présumé du public.
    - Profession : Faire référence aux centres d’intérêt professionnels et aux besoins pertinents pour ce public.
    - Identifier les intérêts et besoins du public.

    2. Sujets d’intérêt
    - Problèmes et solutions : Identifier les défis courants rencontrés par ce public et proposer des conseils concrets.
    - Tendances et préférences : Se tenir informé de ce qui attire actuellement ce groupe et l’intégrer lorsque possible.

    3. Style et clarté appropriés
    - Aligner le ton général (amical, professionnel, etc.) avec ce à quoi le public répond généralement.
    - Garder les explications simples, en évitant les termes trop techniques ou obscurs sauf si cela convient au public.
    - Utiliser des exemples et analogies pertinents qui résonnent avec leur quotidien.

    4. Contenu informatif
    - Offrir des perspectives nouvelles ou des approches originales sur des sujets qui comptent pour le public.
    - Être authentique : Maintenir honnêteté et clarté pour instaurer la confiance.
    - Citer des sources fiables ou des faits si nécessaire pour renforcer la crédibilité.
    - Se concentrer sur la production d’un contenu bien documenté et de haute qualité plutôt que sur la quantité.

    5. Respecter les normes culturelles et sociales
    - Refléter et respecter les valeurs et croyances importantes pour le public.
    - Rester attentif aux opinions divergentes au sein du groupe, en présentant le contenu de manière respectueuse et inclusive.
    """

    REFERENCES_KEYWORDS_EXTRACTION_TEMPLATE = """
    Your task is to extract the most relevant and popular keywords from the given list of texts (up to 10 results).
    Your main task is to select the most relevant, most interesting and most important keywords from these texts that will be used in SERP API.
    If there is a time period, convert it to a suitable short phrase for SERP API in the context of the given content.
    Note: use {language} language.

    Tasks:
    1. Identify only the most relevant and meaningful keywords or entities that are relevant to the topic of the page and can be used in SERP API to find pages on the main 
    topic of <p> tags.
    2. Focus on keywords that reflect the core topic and align with user intent.
    3. Prioritize keywords that are named entities, proper names, brands, etc. It is crucial to select the most 
    interesting and deep keywords that reflect the essence of the text.
    4. Output keyword must be short phrase or a single word suitable for SERP API that will trigger unique links on the content topic.
    5. Try to select unique keywords within different texts that can lead to different links.
    6. Do not select too general keywords. Selected keywords must lead to links that are relevant to the essence of the text.
    7. Sort the keywords by their appearance in the text.
    
    Input:
        A list of texts from the page with their UUIDs: ["text1", "text2", ...]
    
        {texts_list}
    
    Output format:
        A Python list with related keywords:
        
        data:
            ["keyword 1", "keyword 2"]
    """

    REFERENCES_URL_SELECTOR_TEMPLATE = """
    Your task is to select only the most relevant, and meaningful website link from the given list 
    of python dictionaries with websites metadata information.
    
    Example of list:
            [
                {{
                    "title": "title1",
                    "link": "link1"
                    "description": "description1"
                }},
                {{
                    "title": "title2",
                    "link": "link2"
                    "description": "description2"
                }},
                ...
            ]

        Each dictionary contains information about url address, title in google search and description.

    Tasks:
        1. Focus on website that reflect the keyword.
        2. Use context of title and description to check keyword on compatibility.
        3. Select one the most suitable website url which potentially can describe keyword.

    Input:
        keyword = {keyword}
        websites metadata dictionaries = {metadata_list}

    Output format:
        Python string of selected website link.

    Constraints:
        - Do not modify link in the output.
        - Ensure that only the most relevant, and diverse website link is chosen.
        - Do not add additional commentaries or annotation.
        - Do not left output empty.
     """

    PAGE_METADATA_PROMPT = """
    Based on the following summary of web page content (the topic is '{topic}'), generate clickable page title and engaging H1 in {language} language that is:

    1. SEO-optimized :
        - Include high-value, relevant keywords naturally;
        - Match real-world search queries and user intent;
        - Follow best practices for metadata: clear, concise, and clickable;

    2. CTA- and user-focused:
        - Encourage curiosity, clicks, or action using questions or solution framing;
        - Use a helpful, confident tone that promises value to the reader;
            
    3. Key-word driven and consistent:
        - Ensure strong semantic alignment between title and H1. They must be semantically similar and contain the same keywords, 
          so when user clicks on the page title they don't see an H1 which is semantically different from title.
        - Title and H1 must support the same intent and specificity. If the keyword implies comparison, guide, booking etc., both title and H1 should reflect the exact purpose.
        - The H1 must not repeat the title word-for-word. It should restate, expand, or clarify it in a natural way.
        - Avoid shifting focus (e.g., title implies 'book a train ticket' but H1 talks about 'travel tips' - incorrect).

    4. Localization and time
        - Include the country (<<{country}>>) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the user keyword '{keyword}'.
          If you mention country, ensure you mention it in both, H1 and title.
        - Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.

    5. Relevant to the search intent of the page. Search intent is <<{search_intent}>>.

    Adjust title and H1 based on the search intent:

    - If the page is **INFORMATIONAL**:
        - Title: Clear, keyword-aligned, often in how-to or question form;
        - H1: Slightly expanded or natural restatement of the title, guiding or explanatory tone.

    - If the page is **COMMERCIAL**:
        - Title: Action-oriented, value-focused, may include modifiers like “best”, “top”, “affordable”, etc.;
        - H1: Reinforces the offer, benefits, or outcome in an engaging way.

    - If the page is **NAVIGATIONAL**:
        - Title: Compares two or more alternatives; title must emphasize that it's a comparison page;
        - H1: Slightly expandded restatement of the title implying comparison.

    Now, generate in {language} language:
    - Page title (max 60 characters):
    - H1 heading (max 70 characters):

    Output format:
    {{"title": <generated title>, "h1": <generated H1>}}

    **Important: make sure that titles and H1 are formatted exactly as in examples above, in standard sentence case. Don't use title case**

    Create title and H1 headers for given this page summary:
    {content}
    """

    PAGE_METADATA_ASSISTANT_FR = """
    Refer to the following examples:
    
    **Exemple 1**
    Input:
    "topic": "Montres connectées pour le sport",
    "keyword": "meilleure montre connectée sport 2025",
    "intent": "commercial",
    "country": "FR",
    "language": "FR",
    "summary": "Un comparatif actualisé des meilleures montres connectées pour le sport en 2025, mettant en avant des modèles comme la Garmin Forerunner 265 et la Polar Vantage V3, avec un focus sur l’autonomie, la précision GPS et les fonctionnalités fitness."

    Output:
    → "title": "Meilleures montres connectées sport en 2025"
    → "h1": "Top montres connectées pour le sport – Comparatif 2025"

    **Exemple 2**
    Input:
    "topic": "Sommeil et hygiène de vie",
    "keyword": "améliorer la qualité du sommeil naturellement",
    "intent": "informational",
    "country": "FR",
    "language": "FR",
    "summary": "Ce guide explore les méthodes naturelles pour améliorer la qualité du sommeil : routines nocturnes, alimentation, exposition à la lumière, respiration et relaxation. Des conseils d’experts en santé du sommeil sont également inclus."

    Output:
    → "title": "Comment améliorer naturellement la qualité de votre sommeil ?"
    → "h1": "Méthodes naturelles pour mieux dormir au quotidien"

    **Exemple 3**
    Input:
    "topic": "Comparatif plateformes de cours en ligne",
    "keyword": "Udemy vs Coursera",
    "intent": "navigational",
    "country": "FR",
    "language": "FR",
    "summary": "Une analyse approfondie de Udemy et Coursera, comparant leur offre de cours, les prix, les certifications, la qualité des enseignants et les retours utilisateurs afin d’aider à choisir la bonne plateforme selon vos besoins."

    Output:
    → "title": "Udemy vs Coursera : quelle plateforme de cours en ligne choisir ?"
    → "h1": "Comparatif Udemy ou Coursera – Avantages, prix et recommandations"
    """

    PAGE_METADATA_ASSISTANT_US = """
    Refer to the following examples:

    **Example 1**
    Input:
    "topic": "Budget gaming laptops",
    "keyword": "cheap gaming laptops 2025",
    "intent": "commercial",
    "country": "US",
    "language": "US",
    "summary": "A detailed review of the best gaming laptops under $1000 in 2025, including models like the Dell G16 and MSI Katana A15. Focus on performance, GPU value, and affordability for gamers on a budget."

    Output:
    → "title": "Best cheap gaming laptops for 2025";  
    → "h1": "Top budget gaming laptops under $1000 – 2025 buying guide";

    **Example 2**
    Input:
    "topic": "Posture correctors",
    "keyword": "posture corrector for back pain",
    "intent": "informational",
    "country": "UK",
    "language": "US",
    "summary": "An expert guide to selecting the right posture corrector for different types of back pain. Includes comparisons of brace styles, usage tips, and physiotherapist recommendations."

    Output:
    →"title": "Posture correctors for back pain: what works?",
    →"h1": "Choosing the right posture corrector for back pain relief"

    **Example 3**
    Input:
    "topic": "AI writing tools",
    "keyword": "Jasper vs Copy.ai",
    "intent": "navigational",
    "country": "US",
    "language": "US",
    "summary": "A side-by-side comparison of Jasper and Copy.ai, covering pricing, features, supported use cases, and real-world performance tests to help users choose the best AI writing assistant."

    Output:
    → "title": "Jasper vs Copy.ai: Which AI writing tool is better?"  
    → "h1": "Jasper vs Copy.ai – A detailed comparison of top AI writing tools"
    """


class TweetThemes(StrEnum):
    INDUSTRY_TOPIC = "prompts a discussion of some topic in your industry"
    INDUSTRY_STORY = "shares a relatable industry-related story"
    INDUSTRY_JOKE = "tells a industry-related joke"
    INDUSTRY_INSIGHT = "provides an insight of something industry-related"
    WORK_STORY = "tells a story from work"
    NON_WORK_STORY = "lightens a mood with a non-work related story"


class RequestType(StrEnum):
    STANDART = "standart"
    STRUCTURE = "structure"
    SUMMARY = "summary"
