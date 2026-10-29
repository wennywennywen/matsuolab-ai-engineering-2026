
## 基礎レベル 
### 基礎レベル note

Part 1: dividing by the temperature
Step 1. The model gives each candidate word a raw score. These aren't percentages yet:

Word	Raw score
Paris	4
a	    2
located	1
Step 2. Divide every score by the temperature.

Word	T = 0.5 (low)	T = 1 (default)	T = 2 (high)
Paris	4 ÷ 0.5 = 8	4	4 ÷ 2 = 2
a	    2 ÷ 0.5 = 4	2	2 ÷ 2 = 1
located	1 ÷ 0.5 = 2	1	1 ÷ 2 = 0.5
Compare the gap between Paris and "a":

At T = 0.5, the gap is 8 − 4 = 4. The gap got bigger ("stretched").
At T = 2, the gap is 2 − 1 = 1. The gap got smaller ("shrunk").
Step 3. Turn the scores into percentages. The formula (called softmax) exaggerates gaps, so a bigger gap makes the top word win by much more:

Word	T = 0.5	T = 1	T = 2
Paris	98%	    84%	    63%
a	    2%	    11%	    23%
located	0.2%    4%	    14%
Low temperature: Paris almost always wins.
High temperature: the other words get a real chance.
Part 2: "sampled randomly"
The model doesn't always pick the top word. It picks randomly, weighted by those percentages, like drawing a ball from a bag.

At T = 1, imagine a bag with 100 balls:

84 balls say "Paris"
11 balls say "a"
4 balls say "located"
Each time the model needs a word, it draws one ball. Usually you get "Paris", but sometimes you get "a", and the sentence then continues differently: "The capital of France is a city known for…"

This happens for every word in the answer, so one different draw early on changes everything after it. That's why asking the same question twice gives different answers.

At T = 0.5, the bag is 98 Paris balls, so the answers are almost always the same.
At T = 2, the bag is much more mixed, so the answers vary a lot.

### 基礎レベル answer 

from google.genai import types   # add near the other imports at the top

```jsx
response = client.models.generate_content(
    model=MODEL,
    contents=question,
    config=types.GenerateContentConfig(temperature=0.2),
)
```
IMPORTANT!! adding another argument about temperature in the config!!

##　実装レベル

1. Imports (lines 13-19)

```jsx
import argparse
from google import genai
from google.genai import errors
from google.genai import types
from app.config import MODEL, api_error_message, get_api_key
```

Import	What it's for
argparse	reads the question you type in the terminal (Python standard library)
genai	Google's Gemini SDK; genai.Client talks to the API
errors	the exception types the SDK raises, like APIError
types	data classes such as Content (a message) and Part (its text)
app.config	shared project settings: model name, API key, error messages
Concept: settings like the API key and model name live in config.py and come from environment variables, not from the code. That keeps secrets out of git and lets you switch models with AIE_MODEL=... without editing code.

2. ask(): one call to the LLM (lines 25-31)

```jsx
def ask(client: genai.Client, history: list[types.Content]) -> str:
    response = client.models.generate_content(model=MODEL, contents=history)
    usage = response.usage_metadata
    print(f"[トークン] 入力: ... / 出力: ...")
    return response.text
```

**IMPORTANT!!** generate_content is the actual API call: it sends the whole history and gets one reply.
response contains more than text. usage_metadata holds the token counts, which is what you pay for and what rate limits are based on.
Concept: **this function does one job (send, then return the reply)**. It doesn't create the client or manage history; that's main()'s job. Keeping responsibilities separate like this makes code easier to change.

3. message(): building one message (lines 33-34)

```jsx
def message(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])
```

Gemini expects each message in this shape:
Content
 ├─ role:  "user" or "model"   ← who said it
 └─ parts: [Part(text="...")]  ← a list, because one message can hold text, images, and so on
Concept: a small helper avoids writing that long expression twice (DRY: "Don't Repeat Yourself").

4. main(): the chat loop (lines 37-71)
This is the most important part.

Setup, done once

```jsx
client = genai.Client(api_key=get_api_key())
history: list[types.Content] = []
question = args.question
```

```jsx
client = genai.Client(api_key=get_api_key())
```
This makes a client object and gives it your API key. From then on, every request through client is automatically sent with that key, so you only pass the key once.
Under the hood, talking to Gemini means sending HTTP requests over the internet to Google's servers. Without a client, you'd have to:
    build the request URL,
    attach your API key to every request,
    turn your messages into JSON,
    send the request and wait,
    parse the JSON response,
    handle errors.
The client does all of that for you. You call a Python method, and it handles the network part.

The loop which start below, repeated every turn
```jsx
    while True:
        print(f"[質問] {question}\n")
        history.append(message("user", question))
        try:
            answer = ask(client, history)
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            history.pop()  # failed question isn't part of the conversation
        else:
            history.append(message("model", answer))
            print(answer)

        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+C
            break
        while not question:  # ignore empty Enter
            question = input("> ").strip()
        if question in ("exit", "quit"):
            break
```
What each piece does

```jsx
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
```

Two details to notice
1. **Why the first question doesn't need input()**. Before the loop, line 49 sets question = args.question, the question from the terminal command. The first pass through the loop uses that. From the second pass on, question comes from input() at line 65 because input() is the only way in this program to get new text from you after the program has started

2. break exits the loop, not the program. After break, Python continues after the loop. Nothing comes after it in main(), so the function ends, and with it the program.


Concepts to understand
a) The API has no memory. This is the main lesson of the 実装 homework. Each call to generate_content starts fresh. The model only "remembers" because you resend the entire conversation every time. After three turns, the call sends:
[user Q1, model A1, user Q2, model A2, user Q3]
This means the input tokens grow every turn, so long chats become slower, more expensive, and eventually hit the model's context limit. Every chat app (ChatGPT, Claude, and so on) has to deal with this.

b) try / except / else
try:
    answer = ask(client, history)       # might fail
except errors.APIError as e:
    ...                                 # runs only if it failed
    history.pop()
else:
    history.append(message("model", answer))  # runs only if it succeeded
else keeps the "success" code separate from the "risky" line, so only ask() is protected.

c) **Why history.pop()?** If the call fails, your question has no answer. Without removing it, the history would contain two user messages in a row, which confuses the model. Keep the history consistent: user and model messages alternate.

d) Exiting cleanly. input() raises EOFError on Ctrl+D and KeyboardInterrupt on Ctrl+C. Catching them lets the program end quietly instead of printing a traceback.

e) **while True + break.** This is the standard pattern for "loop until the user says stop".

5. if __name__ == "__main__": (lines 74-75)

if __name__ == "__main__":
    main()
This runs main() only when the file is executed directly, as in python -m app.ask. When another file imports it, for example the test that imports DEFAULT_QUESTION, main() does not run.



