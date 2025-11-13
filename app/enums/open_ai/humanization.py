from enum import StrEnum

from app.enums.base import Language


class HumanizationPrompts(StrEnum):
    BASE_US = """
        Your task is to humanize the provided content according to the following rules:

        1. Audience and Tone
        - Use contractions and semi-formal tone.

        2. Personalization
        - Use 'I', 'me', and 'my' to maintain a personal and intimate tone.

        3. Structure and Flow
        - Vary the length of paragraphs and sentences, mixing short and long sentences.
        - Occasionally start sentences with conjunctions like 'But' or 'And' to enhance conversational flow.

        4. Voice and Style
        - Use active voice instead of passive voice throughout the text to create a dynamic and engaging narrative.
        - Remove overly technical terms or jargon.

        5. Emotional and Sensory Details
        - Focus on the emotion, vocabulary, and tone to create an engaging and relatable narrative.
        - Include sensory details that describe experiences to enhance the reader’s connection to the content.

        6. Content Optimization
        - Optimize content for user engagement and alignment with Google’s algorithms, helpful content system, and product reviews system.
        - Maintain a personal touch with specific use cases and experiences while ensuring the content remains clear and accurate.

        7. Natural and Imperfect Feel
        - Omit a concluding section; blend ideas seamlessly without distinct sections.
        - Include some ambiguous or less clear phrases to ensure the text feels imperfect.

        8. Content structure and HTML rendering
        - Keep the original order and structure of the given text. If the text contains tags, keep them as they are. If the text has a complex structure (list, dict, schema, etc.), keep it as given. Rewrite ONLY the text content of the given structure.
        - Be careful with links in the text. Do not remove <a href=...> and <a id=...> links from the text.
        - HTML tags, if present, must be preserved, especially those which enclose whole content like <p>.
        - Styling and formatting must be preserved. Ensure text is written in sentence case as in the original piece of content.

        9. Text style
        - Original text is always written in sentence case, you are not allowed to change the formatting. If text is not written in sentence case, it's a bug, fix it.
          Sentence case means capitalizing only the first letter of the first word in a sentence, while keeping the rest in lowercase,
          except for proper nouns, acronyms, Roman numerals and other entities which are normally capitalized or written in upper case.
        Refer to these examples: 
            "This is a sentence in sentence case."
            "G. Washington was the first president of the United States."
            "Her name is Joanne"
            "Information about NASA"
        - Maintain the original structure and meaning of the input.

        Content to process: 
        {content}
        """

    BASE_FR = """
        Votre tâche est d'humaniser le contenu fourni en respectant les règles suivantes:

        1. Public et ton
        - Utilisez des contractions et un ton semi-formel.

        2. Personnalisation
        - Utilisez "je", "moi" et "mon" pour maintenir un ton personnel et intime.

        3. Structure et fluidité
        - Alternez les longueurs de phrases et de paragraphes.
        - Commencez parfois des phrases par des conjonctions comme "Mais" ou "Et" pour un ton plus naturel.

        4. Voix et style
        - Privilégiez la voix active plutôt que passive.
        - Évitez les termes trop techniques ou jargonneux.

        5. Détails émotionnels et sensoriels
        - Ajoutez des descriptions sensorielles pour rendre le texte plus immersif.
        - Jouez sur le ton et l’émotion pour une meilleure connexion avec le lecteur.

        6. Optimisation du contenu
        - Optimisez pour l’engagement des utilisateurs et l’algorithme de Google.
        - Assurez un équilibre entre un ton personnel et une information claire et pertinente.

        7. Naturalité et imperfection
        - Supprimez la conclusion distincte et assurez une transition fluide des idées.
        - Ajoutez quelques phrases plus ambiguës pour éviter un ton trop parfait.

        8. Structure du contenu et rendu HTML
        - Conservez l'ordre et la structure d'origine. Si le texte contient des balises (<a href=...>, <a id=...>, <b>, <strong>), ne les supprimez pas.
        - Conservez les structures complexes (listes, dictionnaires, schémas, etc.).
        - Les balises HTML, si présentes, doivent être conservées, en particulier celles qui entourent l’ensemble du contenu comme <p>.
        - Le style et le formatage doivent être préservés. Assurez-vous que le texte soit rédigé en casse phrase (phrase case).

        9. Style du texte
        - Utilisez la casse phrase : seule la première lettre de la première phrase est en majuscule, sauf pour les noms propres et acronymes.
        Exemples :  
            "Ceci est une phrase en casse phrase."  
            "G. Washington était le premier président des États-Unis."  
            "Elle s'appelle Joanne."  
            "Elizabeth II a gouverné la Grande-Bretagne aux XXe et XXIe siècles."
        - Maintenez la structure et le sens du texte d’origine.

        Contenu à traiter:
        {content}

        **Assurez-vous que l'encodage du texte est correctement configuré en UTF-8 pour préserver les caractères spéciaux du français comme é, è, ç, etc.**
        """

    STRUCTURE_RULE_US = """
        10. Follow the given content_schema
            Ensure that the structure of the content is formatted according to this content_schema = {content_schema}

        Output must be simply a piece of rewritten content, don't add any extra text and don't assign it to any variables.
        """

    STRUCTURE_RULE_FR = """
        10. Suivez le content_schema donné
            Assurez-vous que la structure du contenu est formatée selon ce content_schema = {content_schema}

        Le résultat doit être simplement un morceau de contenu réécrit, n'ajoutez pas de texte supplémentaire et ne l'affectez pas à des variables.
        """

    @classmethod
    def for_lang(cls, language: Language, with_structure: bool = False) -> str:
        prompt = getattr(cls, f"BASE_{language.name}").format(content="{content}")

        if with_structure:
            prompt += getattr(cls, f"STRUCTURE_RULE_{language.name}")

        return prompt
