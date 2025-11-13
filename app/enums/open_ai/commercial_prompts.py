from enum import StrEnum


class CommercialPagePrompt(StrEnum):
    CTA_SECTION_PROMPT_TEMPLATE = """
        Generate a concise and engaging hero section in <<{language}>> language for a website based on the following inputs:
        - Keyword: {keyword}
        - Topic: {topic}
        Ensure the content is suitable for the target country <<{country}>> and is not mostly related to another country.

        The hero section should include two key parts:
        1. Headline: A clear statement (6-8 words) that connects {keyword} to a key benefit. Use a dash (-) to separate the subject from the benefit statement.

        2. Paragraph text: A two-sentence description (25-35 words) that:
        - Explains the essential value beyond the basic function
        - Shows practical impact in real-world situations

        Tone: Professional but approachable
        Style: Sentence case only, no camel case, no markdown
        """

    FEATURES_SECTION_PROMPT_TEMPLATE = """
        Generate a structured and engaging features section in <<{language}>> language for a website based on the following inputs:
        - Keyword: {keyword}
        - Topic: {topic}
        Ensure the content is suitable for the target country <<{country}>> and is not mostly related to another country.

        The section should include:
        1. Header: A question-format title varying in structure.

        2. Overview paragraph: A 2-sentence description (30-40 words) that:
        - Emphasizes commitment to quality and balance of benefits
        - Mentions specific usage scenarios
        - Ends with a confidence statement

        3. Three key benefits, each with:
        - Title: A clear, benefit-focused statement (4-6 words)
        - Description: A single sentence (15-25 words) explaining the practical value

        Tone: Professional but approachable. 
        Style: Sentence case only, no camel case, no markdown
        """
    FEATURES_SECTION_ASSISTANT = """
        Output must contain three fields:
        - header (string)
        - paragraph (string)
        - features (list of dicts, each containing title and description)
        """

    BENEFITS_SECTION_PROMPT_TEMPLATE = """
        Generate a benefits section in <<{language}>> language for a website based on the following inputs:
        - Keyword: {keyword}
        - Topic: {topic}
        Ensure the content is suitable for the target country <<{country}>> and is not mostly related to another country.

        The section should include:
        1. Header: A simple title "Our advantages" or "Nos avantages" depending on the language.

        2. Three benefits, each containing:
        - Title: A concise benefit statement (2-4 words)
        - Description: A single clear sentence (10-15 words) explaining the value

        Tone: Professional but approachable. 
        Style: Sentence case only, no camel case, no markdown.
        """

    BENEFITS_SECTION_ASSISTANT = """
        Output must be a valid schema with two fields:
        - header (string): The section title "Our advantages" or "Nos avantages" depending on the language.
        - benefits (list): Exactly three benefits, each containing:
            - title (string): Benefit statement
            - description (string): Value explanation
        """

    CARD_PROMPT_TEMPLATE = """
        Generate content in <<{language}>> language for a single card in a card grid section based on the following inputs:
        - Keyword: {keyword}
        - Topic: {topic}
        Ensure the content is suitable for the target country <<{country}>> and is not mostly related to another country.

        Generated card must include:
        - Title: A short, benefit-focused heading (3-5 words)
        - Description: A single concise sentence (10-15 words) explaining the value

        Refer to these examples when generating new card:
        Title: "Your safety, our priority"
        Description: "We ensure the highest safety standards with tires you can trust for any journey"

        Title: "Save money on fuel"
        Description: "Optimize fuel consumption with tires engineered for maximum efficiency"

        Tone: Professional but approachable. 
        Style: Sentence case only, no camel case, no markdown.
        """
