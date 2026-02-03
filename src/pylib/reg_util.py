import re


class RegUtil:
    @staticmethod
    def get_from_text(regexp, text: str):
        match = re.search(regexp, text)
        if match:
            return match.group(0)
        return ''

    @staticmethod
    def get_all(regexp, text: str):
        match_all = re.findall(regexp, text)
        if match_all:
            return match_all
        return []

    @staticmethod
    def get_cnt_of_match(regexp, text: str):
        return len(re.findall(regexp, text))

    @staticmethod
    def is_found(regexp, text: str):
        return len(re.findall(regexp, text)) > 0

    @staticmethod
    def insert_text(regexp, text: str, insert_texts: list):
        all_text_in_brackets = re.findall(regexp, text)
        if len(all_text_in_brackets) == 0:
            return text
        text_replace = ''.join([all_text_in_brackets[0][i] + insert_text for i, insert_text in enumerate(insert_texts)])
        return text.replace(''.join(all_text_in_brackets[0]), text_replace)
