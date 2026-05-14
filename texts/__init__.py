def get_texts(lang: str):
    if lang == "uz":
        import texts.uz as t
        return t
    import texts.ru as t
    return t
