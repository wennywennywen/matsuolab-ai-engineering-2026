"""第1回: 素のLLMに1回だけ質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

ツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def ask(client: genai.Client, history: list[types.Content]) -> str:
    response = client.models.generate_content(model=MODEL, contents=history)

    usage = response.usage_metadata
    print(f"[トークン] 入力: {usage.prompt_token_count} / 出力: {usage.candidates_token_count}\n")

    return response.text

def message(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    # make a parser
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    # make parser to add the attribute name for the stuff you type in terminal as "question"
    # "question" has no - or -- in front of it, so it's a positional argument. argparse fills positional arguments in the order you declared them with add_argument
    args = parser.parse_args()
    # parse_args is a method come from the import that help parser to read whats in the terminal 
    # parser read then store everything in args

    client = genai.Client(api_key=get_api_key())
    history: list[types.Content] = []
    question = args.question

    print(f"[model] {MODEL}  （終了するには exit）")
    while True:
        # loop start: while True repeats forever until a break
        print(f"[質問] {question}\n")
        # print the question: shows what's being asked
        history.append(message("user", question))
        # add to history: message("user", ...) builds the message; .append adds it to the end of the list
        try:
            answer = ask(client, history)
            # call ask: sends the full history to Gemini and gets the reply text
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            history.pop()
            # error branch: runs only if ask() failed; .pop() removes the last item (your unanswered question)
        else:
            history.append(message("model", answer))
            print(answer)
            # success branch: else runs only if ask() succeeded; saves the reply so the next turn remembers it

        try:
            question = input("\n> ").strip()
            # read next question: input("\n> ") waits for you to type; .strip() removes extra spaces and newlines
        except (EOFError, KeyboardInterrupt):
            break
            # Ctrl+D / Ctrl+C: those keys make input() raise an exception; catching it and calling break leaves the loop
        while not question:
            question = input("> ").strip()
            # empty input: an empty string counts as false, so while not question keeps asking until you type something
        if question in ("exit", "quit"):
            break
            # exit / quit: checks whether the text is one of those words, then break
        # back to start: end of the loop body, so Python jumps back to "while True" with the new question


if __name__ == "__main__":
    main()
