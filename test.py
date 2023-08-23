import string


def replace_letters_with_underscores(input_string, exclude_words=None):
    if exclude_words is None:
        exclude_words = []

    words = input_string.split()
    result = []
    for word in words:
        inner_result = []
        if word.lower() in exclude_words:
            result.append(word)
        else:
            for letter in word:
                if letter.isalpha():
                    inner_result.append("_")
                else:
                    inner_result.append(letter)
        result.append(''.join(inner_result))
    cleaned_text = ' '.join(result)
    return cleaned_text


print(replace_letters_with_underscores("teEDst! me",["me"]))
