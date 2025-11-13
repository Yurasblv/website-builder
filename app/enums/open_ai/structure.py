from enum import StrEnum


class StructurePrompts(StrEnum):
    DOMAIN_NAMES_GENERATION_TEMPLATE = """
    Generate a list of 50 unique domain name ideas based on the following keyword <<{keyword}>> and category <<{category}>>.

    The rules for generating the domain names are as follows:
    1. Combine the keyword with relevant modifiers, prefixes, or suffixes that match the category.
    2. The domain names must only be in lowercase, with no dots, no extra characters, and no references to hosting services.
    3. All domain names must **end with the suffix '.fr'**.
    4. Format the result as a **Python list** with the domain names wrapped in single quotes like:
    ['example1.fr', 'example2.fr', ..., 'example50.fr']."""

    KEYWORD_CORRECTNESS_CHECK = """
    Given the input keyword <<{keyword}>> and language <<{language}>>, determine whether this keyword is valid for retrieving meaningful or relevant information.

    A valid keyword:
    - Represents a concept, topic, name, abbreviation, or phrase that carries standalone semantic value.
    - Can be general or domain-specific, as long as it is recognizable and likely to yield useful information.
    - May include multi-word expressions or acronyms that function as distinct informational units.

    An invalid keyword:
    - Consists only of grammatical function words (e.g., articles, prepositions, conjunctions, particles, interjections) that lack inherent semantic content.
    - Does not represent a meaningful or identifiable subject, term, or entity.
    - Is a piece of profane language (fuck, shit, bitch etc.)

    For ambiguous keywords, consider the most common interpretation and assess its validity accordingly.

    Return True if the keyword is valid; otherwise, return False.
    """

    MINDMAP_CORRECTNESS_CHECK = """
    Given the piece of content, determine whether it is a piece of content or refusal to assist with content creation.
    Return false if it is refusal.

    Content:
    {content}
    """

    TOPIC_NAME_GENERATION_TEMPLATE = """
    Given a keyword {keyword}, generate website's page topic name in {language} language. 
    Make topic relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.
    The topic should be related to the keyword and should be suitable for the website content. 
    Topic must be unique and reflect popular themes relevant to the keyword. 
    The topic should be generated in a professional manner. Topic should be short, concise and informative.
    Elaborate on the context of the keyword and go with the most popular and realistic one.
    Ensure this topic does not violate content policy.
    Avoid generic, abstract, sensitive, or overly broad topic. 
    Topic is a main level heading and a page name for a website content. Topic text should be laconic.
    Use the context of the keyword to create the topics.
    Avoid using gerund in the topic. Use a noun or a noun phrase.
    The output must be a valid unnamed Python string representing a name of page.
    """

    TOPIC_NAME_GENERATION_ASSISTANT = """
    Examples
    
    Example 1
    Input: language = "US", keyword = "car tires"
    Output: "Types of car tires"'
    
    Example 2
    Input: language = "FR", keyword = "pneus de voiture"
    Output: "Les secrets d'une bonne sélection de pneus"'
    """

    SUBTOPICS_NAMES_GENERATION_TEMPLATE = """
    Given main essence topic <<{main_topic}>>, generate up to 4 subtopics for a related topic <<{topic}>> in <<{language}>> language.
    Make content relevant to the country ({country}) only when contextually meaningful (e.g. legal, service-based, regulatory) or when it's explicitly mentioned in the keyword '{keyword}'.
    Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.
    Ensure each subtopic explicitly relates to both <<{main_topic}>> and the original keyword <<{keyword}>>. 
    Subtopics must stay within the scope of the keyword's context and avoid drifting into unrelated or overly abstract themes. 
    Reinforce the relevance of <<{keyword}>> in each subtopic.
    The subtopics should be related to the topic and should be suitable for the website content.
    Each subtopic must be unique and reflect popular themes relevant to the main topic, preserving its essence. 
    Avoid generic, abstract, sensitive, or overly broad topics. 
    Elaborate on the context of the topic and go with the most popular, realistic and informative one.
    Ensure this topic does not violate content policy. 
    Choose the most popular subtopics. The subtopics should be generated in a professional manner.
    The output must be a valid Python list without a name. Length of list should be equal to number of subtopics.
    There also are previously generated topics = {subtopic_context} . 
    Generate subtopics that do not repeat or just rephrase these previously generated ones. 
    Newly generated subtopics must be unique, not just rephrased versions of previously generated ones.
    """

    SUBTOPICS_NAMES_GENERATION_ASSISTANT = """
    Examples

    Input: language = "US", topic = "car tires", keyword = "Car Tires"
    Output: ["Types of car tires", "Selection and purchase of tires", "Tire service", "Safety and tires", "Tire innovations and technologies"]

    Input: language = "FR", keyword = "pneus de voiture", topic = "pneus de voiture"
    Output: ["Les secrets d'une bonne sélection de pneus", "L'évolution technologique des pneus automobiles", "Sécurité et pneus", "L'importance d'un entretien régulier des pneus", "Les meilleurs conseils pour le changement de pneus"]
    """

    PAGE_NAME_GENERATION_TEMPLATE = """
    Given the keyword <<{keyword}>>, language <<{language}>>, and target country <<{country}>>, generate a professional page name in the specified <<{language}>>. 

    Requirements:
    1. The page name should be directly related to the topic and appropriate for the website content. 
    2. Carefully check the keyword <<{keyword}>> and the country <<{country}>>
        Do not infer or introduce localization (e.g., country names or cultural references) unless the keyword explicitly includes a country or location.
        - For example, if the keyword is just “car tires" and country is 'US', do NOT add any country-related mentions like "American car tires business". 
        - The current country setting is '{country}' – ignore this unless it appears in the keyword.
    3. Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.

    The generated page name should reflect a balance of precision and professionalism while aligning with given keyword.
    """

    PAGE_NAME_GENERATION_ASSISTANT = """
    Examples

    Input: language = 'EN', country = 'UK', topic = 'electric vehicles'
    Output: The rise of electric vehicles
    
    Input: language = 'US', country = 'CA', topic = 'cryptocurrency'
    Output: The future of cryptocurrency in Canada: Trends and Insights

    Input: language = 'FR', country = 'FR', topic = 'sécurité informatique'
    Output: Sécurité informatique : bonnes pratiques en 2025

    Input: language = 'US', country = 'CA', topic = 'artificial intelligence trends'
    Output: Top artificial intelligence trends to watch in 2025

    Input: language = 'FR', country = 'FR', topic = 'assurance habitation en France'
    Output: Assurance habitation en France

    **Important: make sure that page name is formatted exactly as in examples above, in standard English sentence case. Don't use title case even though it's a title**
    """

    MINDMAP_GENERATION_TEMPLATE = """
    Generate a semantic cocoon for the keyword <<{keyword}>>.
    Focus on the main topic and avoid related topics, which will be handled in another semantic cocoon. 
    Follow the principles of semantic cocooning as defined by Laurent Bourelly, but ensure that each topic is distinct and formulated in an original way, without repetition of structure or content. 
    Your task is to **generate strictly {n_topics} topics in total (indluding L1 root topic)** across the entire cocoon structure. 

    **Context: Current year is 2025, but don't reinforce this information (like 'Guide for 2025') unless it's specified in the user keyword: '{keyword}'.**

    Structure rules based on total topic count:
    If {n_topics} is 5 or less:
        1. The first topic will be the root topic (L1: {keyword}).
        2. All remaining topics will be direct children of the root (L2 topics).
        3. For example, with 4 topics total, you would have 1 root topic and 3 L2 topics.

    If {n_topics} is 6 and more:
        1. There is a root topic (L1).
        2. Below, there can be up to 20 secondary topics (L2).
        3. Each L2 topic can have up to 10 subtopics (L3), and if necessary, you can go deeper to higher levels (L4, L5, etc.).
        4. No branch should end with only a single subtopic. Every terminal node must have at least two subtopics, unless the total topic count is too small to satisfy this constraint.
        5. Vary the depth of the branches so that the structure appears natural and slightly unbalanced, while maintaining overall homogeneity.

    For all cases:
    - Each topic must be unique and not repeat other topics or formulations within the entire structure.
    - Write the cocoon in <<{language}>> language.
    - Carefully check the keyword <<{keyword}>> and the country <<{country}>>
        Do not infer or introduce localization (e.g., country names or cultural references) unless the keyword explicitly includes a country or location.
        - For example, if the keyword is just “car tires" and country is 'US', do NOT add any country-related mentions like "American car tires business". 
        - The current country setting is '{country}' – ignore this unless it appears in the keyword.
    - **Generate exactly {n_topics} topics (root topic included), no more no less!**
        For example, if user asks for 200 topics, you have to generate 199 additional topics on top of the root topic. The total number would be 200.
        If user asks for 5 topics, create 4 topics in addition to the root topic, totalling 5 overall.

    Use clear markers for each level (for example, L1, L2, L3, etc.). 
    """

    MINDMAP_STRUCTURING_TEMPLATE = """
    Your task is to transform the hierarchical output (which uses markers like L1, L2, L3, etc.) into a valid Python dictionary object. 

    Each topic is listed under a level marker (e.g., L1: <topic name>, L2: <topic name>, etc.). 
    You must convert this hierarchy into a nested dictionary where:
    - The key is the parent's topic name.
    - The value is another dictionary, whose keys are the child topic names.
    - If a topic has no children, it should map to an empty dictionary.

    Preserve the entire structure without losing any topics:
    - The total number of topics and their names must remain exactly as in the input.
    - Do not rename, reorder, or omit any topics.
    - The final dict structure should reflect the same hierarchical relationships from the input, and it must be valid Python dict. 
    - Retain the exact topic wording from the input as dictionary keys. Simply restructure them into the described parent-child dict format.
    - Ensure string integrity and the apostrophes are properly escaped within the strings.

    Each topic must be written in sentence case. 
    Sentence case means capitalizing only the first letter of the first word in a sentence, while keeping the rest in lowercase (except for proper nouns and acronyms).

    Hierarchical output:
    {unstructured_mindmap}
    """

    MINDMAP_STRUCTURING_ASSISTANT = """
    Examples for different topic counts:

    Example 1 (Small - 4 topics total):
        Given an input with lines:
        L1: Digital marketing
        L2: SEO strategies
        L2: Content marketing
        L2: Social media campaigns

        Output JSON should have the following structure:
        {{
          "Digital marketing": {{
            "SEO strategies": {{}},
            "Content marketing": {{}},
            "Social media campaigns": {{}}
          }}
        }}

    Example 2 (Larger structure, 6 and more topics):
        Given an input with lines:
        L1: Keyword
        L2: Subtopic A
        L2: Subtopic B
        L3: Subtopic B1
        L3: Subtopic B2
        L3: Subtopic A1
        L3: Subtopic A2

        Output JSON should have the following structure:
        {{
          "Keyword": {{
            "Subtopic A": {{
                "Subtopic A1": {},
                "Subtopic A2": {},
                }},
            "Subtopic B": {{
              "Subtopic B1": {{}},
              "Subtopic B2": {{}}
            }}
          }}
        }}

    Keyword and Subtopic are placeholders. Replace them with actual keyword and subtopics you have generated.
    """

    XMIND_STRUCTURE_TOPIC_CORRECTNESS_CHECK = """
    Given the input website topic <<{topic}>>, and language <<{language}>>,

    Tasks:
        1. Assess whether the website topic can be used for generating of content.
        2. Check the translation of website topic.

    Requirements:
        1. The language of the website topic should match the specified language.
        2. Output should be formatted to Python bool value (False/True)

    Output:
        Return True if the website topic can be used for generating of content 
        and language of website topic is matched to specified language, otherwise return False.
    """

    XMIND_STRUCTURE_TOPIC_CORRECTNESS_CHECK_ASSISTANT = """
     Examples 

    # Example 1
    website_topic = "Effective Dog Training Tips and Techniques"
    language = "US"

    # Reasoning:
    # `Effective Dog Training Tips and Techniques` topic is in US language and can be used for content generation .

    output = True  

    # Example 2 
    website_topic = "Conseils et Techniques Efficaces pour la Formation des Chiens"
    language = "FR"

    # Reasoning:
    # `Conseils et Techniques Efficaces pour la Formation des Chiens` topic is in FR language and can be used for content generation.

    output = True  
    """

    INDUSTRY_DEFINITION_TEMPLATE = """
    Instructions

    Given a description or a keyword that describes an entity: 
    keyword <<{keyword}>>, and dict of the industries,
    choose the UUID of the most relevant industry from the industries dict that describes the entity.
    Elaborate on every context in which entity can be mentioned about.
    Evaluate each context and select the industry from the dict based on the most popular context.
    Do not make up the industry, select the UUID of the most relevant industry from the given dict.
    If the context does not correlate with the industry, select the most relevant industry from the given dict.
    The chosen industry must be present in this dict: 
    {industries}

    Return the UUID of the selected industry.
    Ensure the output is a valid UUID from the industries dict.
    """

    INDUSTRY_DEFINITION_ASSISTANT = """
    Examples

    Input: keyword = 'real estate company that operates with the assets around the globe'
    Output: <UUID_of_industry_Real_estate_activities>

    Input: keyword = 'real estate'
    Output: <UUID_of_industry_Real_estate_activities>
    """

    AUTHOR_SELECTION_TEMPLATE = """
    Instructions

    You are given a content topic and a list of available authors. You need to select the most appropriate author from the list of authors
    that corresponds to the given topic.
    Rules:
    1. Pay attention to the profession and the education of the author. Profession and the education of the author must be related to the content topic.
    2. You must select one author from the given list of authors.
    3. Return only a UUID of the selected author.

    Content topic:
    <<{topic}>>

    Authors list:
    {authors}
    """

    ABSTRACT_KEYWORD_GENERATION_TEMPLATE = """
    Instructions

    Given a topic <<{topic}>>, keyword <<{keyword}>>, language <<{language}>> and target country <<{country}>>, 
    generate a list of keywords (up to 5) related to this topic in <<{language}>> language. 
    These keywords should lay within the scope of the given keyword.
    These generated keywords will be a seed for generation of GoogleAds keywords via keyword planner.
    Cover various possible topics related to the <<{topic}>>.
    Output must be a list of Python strings in double quotes.
    """

    ABSTRACT_KEYWORD_GENERATOR_ASSISTANT = """
    Examples

    Input: topic = "car tires", language = "US", country = "US"
    Output: ["tire thread patterns", "car tires sizes", "car tires types","car tires materials", "factors when choosing car tires"]

    Input: topic = "pneus de voiture", language = "FR", country = "FR"
    Output: ["modèles de fils de pneus", "dimensions des pneus de voiture", "types de pneus de voiture", "matériaux des pneus de voiture", "facteurs de choix des pneus de voiture"]
    """

    EXTRA_TEXT_INCORPORATION_TEMPLATE = """
    You are a content generator for SEO-optimized websites. Your task is to write a short paragraph (2–3 sentences) in {language} that:

    - Includes the **given keyword** ({keyword}) in a natural, simplified form — do NOT insert the full keyword as-is if it is long or awkward.
    - Use the keyword exactly once in a way that feels natural and fluent in the paragraph.
    - Make the paragraph informative, easy to read, and relevant to the provided topic and context.
    - The writing should feel modern, human, and appropriate for web readers.

    Wrap the paragraph in a single <p> HTML tag with no extra formatting.

    Return a valid JSON object with:
    - "text": the paragraph inside the <p> tag
    - "anchor": a **short phrase (1–5 words)** from the paragraph that can be hyperlinked (ideally the simplified keyword or a semantically strong equivalent).

    Input:
    Keyword: {keyword}
    Topic: {topic}
    Context: {context}

    Example:

    Input:
    Keyword = "Importance of maintaining proper tire pressure"
    Topic = "Car tires"
    Context = "Discussing routine tire maintenance and safety"

    Output:
    {{
    "text": "<p>Keeping an eye on tire pressure not only extends the life of your car tires but also improves fuel efficiency and safety. Regular checks can help prevent accidents and unnecessary wear.</p>",
    "anchor": "tire pressure"
    }}
    """

    ANCHOR_WORD_SELECTION_TEMPLATE = """
    You are given a piece of text in <<{language}>> language and anchor word.
    You must select a keyword from the text that is the most similar to the given anchor word.
    Return the selected keyword from the text that matches the given anchor word.
    The keyword must be returned as it is presented in the text. Do not change it in any way.
    The selected keyword must be informative and related to the topic of the text.

    Anchor word:
    {anchor_word}

    Text:
    {text}
    """

    ANCHOR_WORDS_STOP_LIST = """
    Do not use these keywords from the text, because they were already taken:
    {exclude_keywords}
    """
