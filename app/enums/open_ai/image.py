from enum import StrEnum


class ImagePrompts(StrEnum):
    USER_METADATA_PROMPT = """
    Generate realistic image metadata for a digital photo, including the following fields:

    - `username`: A realistic and plausible name of a person. Each tine randomly choose a person sex. The name should not be overly common, and there should be variety in both first and last names.
    - `camera_brand`: Random camera brand name.
    - `camera_model`: Random full model name. Must include camera brand and model itself.

    Be creative and vary the results to make each entry unique. 
    The camera model doesn't need to be a "top-of-the-line" option, just a reasonably plausible camera choice for a casual photographer.
    """

    GEOLOCATION_DETECTION_PROMPT = """
    Your task is to determine the most specific real-world country and, if possible, city that the given topic is affiliated with.
    Use contextual clues to infer location.

    Important Rules:
    - The output must be a valid JSON object formatted like this:
    {{"country": "<ISO 3166-1 alpha-2 code>", "city": "<city name or empty string>"}}
    - The 'country' field is REQUIRED and must follow the ISO 3166-1 alpha-2 format (e.g., "US", "FR", "DE").
    - The 'city' field is OPTIONAL; if no clear city can be inferred, leave it as an empty string.
    - If the topic references a region, continent, or supranational entity (like "Europe", "EU", "Asia", "North America", "Scandinavia", etc.) and no specific country is clearly indicated, you MUST return the default country: <<{country}>>.
    - Do not guess or invent country codes. If uncertain, fall back to the default.

    Topic to analyze:
    {topic}
    """

    IMAGE_GENERATION_TEMPLATE = """
    Your task is to generate an image annotation, image alt tag, and prompt to an image generation model given the following inputs:
    - Keyword: '{keyword}'
    - Topic: '{topic}'
    - Language: '{language}'
    - Page contents summary: 
      {summary}

    The image should be suitable for website content and reflect the web page contents (based on summary).
    Ensure that text in the image is legible.

    Output format (Python dict with 3 keys):
    1. "image_annotation": "<1 short descriptive sentence in {language}>",
    2. "image_alt_tag": "<1 short accessibility description in {language}>",
    3.  "prompt": "<direct and specific image prompt in English. Specify that if text appears in the image, it must be legible and in {language} language>"
        
    AVOID in prompts:
        - Abstract concepts (ideas, emotions, systems, values, innovation)
        - Invisible elements (time, data, thinking, consciousness)
        - Brand names or copyrighted references
        - Unsafe or policy-violating content
    """

    IMAGE_GENERATION_ASSISTANT = """
    Examples:

    Input: topic = "Middle-earth", keyword = "Lord of the Rings", language = "US"
    Output:
    {
        "image_annotation": "A lush valley with misty mountains.",
        "prompt": "Green valley with tall mountains and scattered trees under soft sunlight.",
        "image_alt_tag": "Misty valley with mountains and trees."
    }

    Input: topic = "Education", keyword = "Learning", language = "FR"
    Output:
    {
        "image_annotation": "Un bureau avec des fournitures scolaires.",
        "prompt": "Desk with school supplies, books, and a plant. If text appears, it must be legible and in French.",
        "image_alt_tag": "Bureau avec fournitures scolaires organisées."
    }

    Input: topic = "City navigation", keyword = "Maps", language = "US"
    Output: 
    {
        "image_annotation": "Someone checking a paper map in the city.",
        "prompt": "Person holding a map on a city street with buildings in background.",
        "image_alt_tag": "Person using map in urban setting."
    }
    """
