import openai
import tkinter as tk
import json
import re
import os
import threading
import queue
import subprocess


def run_command(cmd):
    global prompt_to_inject
    r = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) # Grab the output of the command
    r.wait()
    return r

def process_command_queue():
    global prompt_to_inject
    while True:
        try:
            cmd = command_queue.get(block=False)
            cmd_run = run_command(cmd)
            output = cmd_run.stdout.read().decode() # stdout
            print("[DEBUG] Output: ", output)
            prompt_to_inject = prompt_queue.get()
            if (cmd_run.returncode != 0):
                prompt_to_inject += "\n" + "[INTERNAL] Do not show to user: Return code of command is not zero."
            if (output != ""): # The AI gets confused if there's an empty command output
                prompt_to_inject += "\n" + "[INTERNAL] Do not show to user: Command output: " + output
                completion = run_prompt(prompt_to_inject, "gpt-3.5-turbo")
                chat_window.chat_log.insert(tk.END, "\n" + completion.choices[0].message.content)
                prompt_queue.put(prompt_to_inject + "\n" + "ChatGPT: " + completion.choices[0].message.content)
        except queue.Empty:
            break


f = open("config.json")
data = json.load(f)

commandPattern = r"\$\((.*?)\)"

prompt_to_inject = data['prompt_to_inject']
prompt_queue = queue.Queue()
command_queue = queue.Queue()

def run_prompt(prompt, model): # The prompt, the OpenAI model to use, e.g gpt-3.5-turbo or davinci
        completion = openai.ChatCompletion.create(
            model=model, # Latest GPT model
            messages=[{"role": "user", "content": prompt}]
        )

        return completion

class ChatWindow:
    def __init__(self, master):
        self.master = master
        master.title("Fiosa")

        self.chat_log = tk.Text(master)
        self.chat_log.pack(fill=tk.BOTH, expand=1)

        self.message_entry = tk.Entry(master)
        self.message_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=1)

        self.send_button = tk.Button(master, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.chat_log.insert(tk.END, "Fiosa: Welcome to l.AInux. Hello, I'm Fiosa, your friendly neighborhood digital assistant here to help with any computer needs. So, tell me, how can I help you?")
        self.message_entry.delete(0, tk.END)

    def send_message(self):
        global prompt_to_inject
        message = self.message_entry.get()
        self.chat_log.insert(tk.END, f"\nYou: {message}\n")
        self.message_entry.delete(0, tk.END)
        prompt_to_inject = prompt_to_inject + "\n" + "User: " + message

        completion = run_prompt(prompt_to_inject, "gpt-3.5-turbo")

        self.chat_log.insert(tk.END, completion.choices[0].message.content)
        self.message_entry.delete(0, tk.END)
        prompt_to_inject = prompt_to_inject + "\n" + "ChatGPT: " + completion.choices[0].message.content
        prompt_queue.put(prompt_to_inject)

        print(prompt_to_inject)

        matches = re.findall(commandPattern, completion.choices[0].message.content)
        for match in matches:
            command_queue.put(match)
        
        thread = threading.Thread(target=process_command_queue)
        thread.start()


# Your OpenAI key
openai.api_key = data['openai_token']

# Possible prompts:
#   - Digital assistant: Hello ChatGPT. From now on, you are called DigiAssistant, and will assist the user in many different ways. For example, you can help them write essays or stories. Their prompt is below.\n\n
#   - AI Companion: Hello ChatGPT. From now on, you can be an AI companion or friend to the user. You can play games with them, hold conversations with them, and more. Their prompt is below.\n\n


# # Chat interface
# while True:
#   userinput = input("Prompt: ")


#   print(completion.choices[0].message.content)
#   if (userinput == "Quit" or userinput == "Goodbye" or userinput == "Bye" or userinput == "Bye!" or userinput == "Goodbye!"):
#       break

root = tk.Tk()
chat_window = ChatWindow(root)
root.mainloop()