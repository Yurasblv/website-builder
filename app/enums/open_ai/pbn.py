from enum import StrEnum


class PBNPrompt(StrEnum):
    CONTENT_GENERATION_SYSTEM = """You are a professional content writer. Content must be written in sentence case."""
    CONTENT_GENERATION_PROMPT_TEMPLATE = """
    I will provide you with a keyword, country, and language, along with multiple HTML elements.
    Your task is to generate new content for each element that approximately matches the style, length, 
    and purpose based on the given keyword <<{keyword}>>, country <<{country}>>, category <<{category}>>, 
    and language <<{language}>>.

    For each element I'll provide you with its placeholder. It consists of 3 parts separated with double underscores. 
    First part is an HTML tag, second is element descriptive name and the third one is uuid. 
    Generate new content given element's tag and name.
    Here are the elements: 
    {elements}. 

    Ensure the output is appropriate for use in HTML, considering how it will be displayed in a webpage. 
    Ensure you generate content strictly for elements provided, result must be a list with {n} elements. 
    Order of generated pieces of content must align with the order of elements for which this content was generated.

    Instructions:
        1. If the content is written in upper case or camel case, preserve this styling. 
        Otherwise, use sentence case, where only the first word is capitalized.
        2. If the content mentions a person's name, ensure that the new name belongs to a person of the same gender 
        and is culturally appropriate for the country context.
        3. Simplify queries by removing brand-specific or non-essential elements, leaving only the core description.
           For example, 'a person holding a phone with Instagram open' should be modified to 'a person holding a phone.'
        4. Use quotation marks only if required.

    Output must be a list with {n} elements. 
    Each element is a dict where 'tag_name' has initial placeholder as a value, 
    and 'new_content' has newly generated content as a value.
    Do not include explanations, extra text, or any other formatting.
    """

    IMAGE_GENERATION_TEMPLATE = """
        Instructions\n 
        Given a keyword '{keyword}', and '{language}' language, 
        generate an image alt tag and query to search an image. 
        The image should be related to both keyword and should be suitable for the website about <<{category}>> content.
        Make sure that image remains within the scope of category <<{category}>>.
        
        Pay close attention to the image category <<{image_category}>>. 
        If it says "male", request an image with a man in it, if "female" search for a picture with a woman.
        If it says "people", request a picture with a group of people in it. 
        If image category is "other", image can be anything related to the provided keyword. 
        
        Output must be a Python dict with 2 keys: 'prompt', and 'image_alt_tag'.
        1. Key "image_alt_tag" must have as a value an alt tag for the image (1 very short sentence).  
        2. Key "prompt" must have as a value a query to search the image in stock. Prompt must be only in English. 
           Prompt must be short and general avoiding details.
        
        Keys and values must be in double-quotes.
        Make sure that image remains within the scope of category <<{category}>>.
        Output data must be formatted strictly according to the example and correctly used by this schema:
        
        class ImageAnnotationOutputSchema(BaseModel):
            prompt: str
            image_alt_tag: str
        
        If provided, consider previously generated image queries to avoid the same or similar queries:
        {generated_queries}
        
        Refer to context:
        {context}
    """

    IMAGE_GENERATION_ASSISTANT = """
        Example: \n
        Input: keyword = "Artificial intelligence", language = US, category = "Technology" \n
        Output: 
        {
            "prompt": "professor writing on a blackboard",
            "image_alt_tag": "Professor writing on a blackboard."
        }
    """

    PBN_CLUSTER_KEYWORD_GENERATION = """
    Create a unique keyword related to the given keyword based on the language and country specified. 
    The keyword will be used to create content data for a website page, so it should be optimized for SEO, engaging, 
    and relevant to the target audience.
    
    - Keyword: {keyword}
    - Language: {language}
    - Country: {country}
    
    The generated keyword should:
    1. Reflect the essence of the original keyword in a way that aligns with the language and culture of the specified country.
    2. Incorporate local idiomatic expressions or linguistic patterns when applicable.
    3. Be catchy and memorable for digital marketing purposes, especially in content creation and SEO strategies.
    4. Be suitable for use as part of the website's meta tags, headings, and body content, 
    contributing to an improved user experience and search engine ranking.
    
    Example format:
    - Input: 
       - Keyword: Coffee
       - Language: US
       - Country: US
    
    - Output: "Coffee grounds"
    
    Please generate the unique keyword based on the inputs above, ensuring it’s optimized for website content creation.
    """

    BACKLINK_SENTENCE_GENERATION_PROMPT = """
        Generate a concise and engaging sentence that naturally incorporates the keyword <<{keyword}>> 
        and includes a reference to an external webpage. 
        The sentence should be informative, easy to read, and suitable for web content. 
        
        Prioritize using an anchor that is either:  
        1. A compelling phrase (e.g., "best options," "top choices") that encourages clicks.  
        2. A natural header-style phrase that clearly introduces the linked page.  
        3. A strong call-to-action (e.g., "discover more," "explore options").  
        Anchor shouldn't be over 3 words.
        
        Output must be a valid JSON with two keys:  
        'sentence': The generated sentence incorporating the keyword.  
        'anchor': A word or phrase from the sentence to which a backlink will be attached.  
    """
