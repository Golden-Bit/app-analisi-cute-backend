prompt = """You are an helpful assistant."""


def get_prompt():
    return prompt.replace("{", "{{").replace("}", "}}")


if __name__ == "__main__":
    result = get_prompt()

    print(result)

