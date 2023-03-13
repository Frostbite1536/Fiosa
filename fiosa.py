import openai
import tkinter as tk
import json
import re
import threading
import queue
import subprocess
import shutil



longterm_memories_file = open("LongTermMemories.txt", 'r')
longterm_memories = longterm_memories_file.read()
longterm_memories_file.close()

def run_command(cmd):
    r = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) # Grab the output of the command
    r.wait()
    return r

def process_command_queue():
    global prompt_to_inject
    global conversation_history
    while True:
        try:
            cmd = command_queue.get(block=False)
            cmd_run = run_command(cmd)
                
            output = cmd_run.stdout.read().decode() # stdout

            print("[DEBUG] Output: ", output)
            if (output):
                prompt_to_inject = prompt_queue.get()
                if (cmd_run.returncode != 0):
                    conversation_history += "\n" + "[INTERNAL] Do not show to user: Return code of command is not zero."
                if (output != ""): # The AI gets confused if there's an empty command output
                    conversation_history += "\n" + "[INTERNAL] Do not show to user: Command output: " + output
            else:
                conversation_history += "\n" + "[INTERNAL] Do not show to user: No output recieved from command."

            print("[DEBUG] Running completion")
            completion = run_prompt(prompt_to_inject, conversation_history, "gpt-3.5-turbo")
            chat_window.chat_log.insert(tk.END, "\n" + completion.choices[0].message.content)
            conversation_history = conversation_history + "\n" + "ChatGPT: " + completion.choices[0].message.content
            prompt_queue.put(conversation_history)

        except queue.Empty:
            break


f = open("config.json")
data = json.load(f)

commandPattern = r"\$\((.*?)\)"

prompt_to_inject = data['prompt_to_inject'] + longterm_memories # The AI's memories
conversation_history = ""
prompt_queue = queue.Queue()
command_queue = queue.Queue()

def run_prompt(systemPrompt, userPrompt, model): # The prompt, the OpenAI model to use, e.g gpt-3.5-turbo or davinci
        completion = openai.ChatCompletion.create(
            model=model, # Latest GPT model
            messages=[{"role": "system", "content": systemPrompt}, {"role": "user", "content": userPrompt}]
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
        global conversation_history
        message = self.message_entry.get()
        self.chat_log.insert(tk.END, f"\nYou: {message}\n")
        self.message_entry.delete(0, tk.END)
        conversation_history = conversation_history + "\n" + "User: " + message

        completion = run_prompt(prompt_to_inject, conversation_history, "gpt-3.5-turbo")

        self.chat_log.insert(tk.END, completion.choices[0].message.content)
        self.message_entry.delete(0, tk.END)
        conversation_history = conversation_history + "\n" + "ChatGPT: " + completion.choices[0].message.content
        prompt_queue.put(prompt_to_inject)

        print(conversation_history)

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

def handle_closing():
    global prompt_to_inject
    global conversation_history

    message = "SYSTEM: Hello Fiosa, this is the System. The user is closing you now, is there anything you would like to add to your long term memories? Reply only with the memories themselves like this 'Memory: <the memory>', nothing else as it will be added directly into your memory."
    chat_window.chat_log.insert(tk.END, "\nFiosa: Goodbye, please wait while I save my memories of this conversation :)")
    chat_window.message_entry.delete(0, tk.END)
    conversation_history = conversation_history + "\n" + "User: " + message

    completion = run_prompt(prompt_to_inject, conversation_history, "gpt-3.5-turbo")

    longterm_memories_file_write = open("LongTermMemories.txt", 'w')
    longterm_memories_file_write.write(completion.choices[0].message.content + "\n") # Save to Fiosa's long-term memory.
    longterm_memories_file_write.close()

    root.destroy()

root.protocol("WM_DELETE_WINDOW", handle_closing)
root.mainloop()