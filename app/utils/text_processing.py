import ast


class TextProcessing:
    @staticmethod
    async def get_dict_from_string(text: str) -> dict:
        """
        Convert a string to a dictionary.

        Parameters:
            text (str): The text to convert.

        Returns:
            dict: The converted dictionary.
        """
        try:
            cleaned_text = text.replace("```python", "").replace("```json", "").replace("```", "")
            output_dict = ast.literal_eval(cleaned_text)

            if not isinstance(output_dict, dict):
                raise ValueError("Parsed output is not a dictionary.")

            return output_dict

        except Exception:
            raise ValueError("Parsing error")
