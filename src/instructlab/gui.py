# native
from subprocess import Popen, PIPE
from time import sleep
import urllib.request
import os
import psutil

# First Party
import instructlab.lab as lab
import instructlab.config as config

# Third-party
import tkinter as tk
from tkinter import ttk


GEOMETRY_W = 1200
GEOMETRY_H = 900

MODELS_FOLDER = 'models'


class GUI:

    def _main_window(self):
        # WINDOW SETUP
        window = tk.Tk()

        # get screen width and height
        ws = window.winfo_screenwidth()  # width of the screen
        hs = window.winfo_screenheight()  # height of the screen

        # calculate x and y coordinates for the Tk root window
        x = (ws/2) - (GEOMETRY_W/2)
        y = (hs/2) - (GEOMETRY_H/2)

        # set the dimensions of the screen
        # and where it is placed
        window.geometry('%dx%d+%d+%d' % (GEOMETRY_W, GEOMETRY_H, x, y))

        return window

    def __init__(self):
        self.WINDOW = self._main_window()

        self.LAB = lab.Lab(config.get_default_config())
        self.DEFAULT_MAP = config.get_dict(self.LAB.config)
        self.SERVER_STARTED = False
        self.SERVER_PROCESS = None

        self.SERVER_MESSAGE = ttk.Label(
            text='server UP' if self.SERVER_STARTED else 'server DOWN', foreground='green' if self.SERVER_STARTED else 'red')
        self.SERVER_MESSAGE.place(relx=0.01, rely=0.97)

        self.CHAT_PANEL = None
        self.TEXT_BOX = None
        self.CHAT_PROCESS = None

        self.MODELS = ["DEFAULT"]
        self.SELECTED_MODEL = None
        self.get_available_models()

    def update_message(self, role, text):
        message = text
        if role == 'ILAB':
            message = "ILAB >>> " + message + "\n---------\n\n"
        elif role == 'USER':
            message = "USER >>> " + message + "\n"
        else:  # assume system
            message = "#### SYSTEM ####\n" + message + "\n################\n"

        self.TEXT_BOX.config(state='normal')
        self.TEXT_BOX.insert('end', '\n'+message)
        self.TEXT_BOX.config(state='disabled')

    def init_lab(self):
        lab.init(["--non-interactive"], standalone_mode=False,
                 obj=self.LAB, default_map=self.DEFAULT_MAP)
        self.update_message(
            "SYSTEM", "<<< INFO >>> ILAB initiated, downloading model....")
        lab.download([], standalone_mode=False)
        self.update_message(
            "SYSTEM", "<<< INFO >>> Model downloaded correctly :)")

        self.update_message("SYSTEM", f"<<< INFO >>> {
            len(self.MODELS)} available {self.MODELS}")

    def get_available_models(self):
        cwd = os.path.join(os.getcwd(), MODELS_FOLDER)
        models = [os.path.join(cwd, f) for f in os.listdir(
            cwd) if os.path.isfile(os.path.join(cwd, f))]
        self.MODELS = ['DEFAULT'] + models

    @staticmethod
    def is_server_started():
        try:
            status = urllib.request.urlopen(
                "http://localhost:8000").status
            return status == 200
        except:
            return False

    def kill_server(self):
        print("bye! :)")
        if self.SERVER_PROCESS is not None:
            for children_pid in (psutil.Process(self.SERVER_PROCESS.pid)).children(recursive=True):
                children_pid.kill()
            self.SERVER_PROCESS = None
        self.WINDOW.destroy()

    def toggle_server(self):
        try:
            # start server with lab
            if not self.SERVER_STARTED:
                self.update_message(
                    "SYSTEM", f"<<< INFO >>> Starting the server with model '{self.SELECTED_MODEL.get()}'...")

                model_path = self.DEFAULT_MAP['serve']['model_path'] if self.SELECTED_MODEL.get(
                ) == "DEFAULT" else self.SELECTED_MODEL.get()
                self.SERVER_PROCESS = Popen(
                    f"source venv/bin/activate; ilab serve --model-path {model_path}", shell=True)

                while not self.SERVER_STARTED:
                    self.SERVER_STARTED = GUI.is_server_started()
                    if self.SERVER_STARTED:
                        self.update_message(
                            "SYSTEM", "<<< INFO >>> Server started correctly :)")
                    else:
                        self.update_message(
                            "SYSTEM", "<<< INFO >>> Waiting for server to start...")
                        sleep(5)
            # stop server
            else:
                # refresh available models for the next execution
                self.update_message(
                    "SYSTEM", "<<< INFO >>> Shutting down the server...")
                self.kill_server()
                while self.SERVER_STARTED:
                    self.SERVER_STARTED = GUI.is_server_started()
                    if self.SERVER_STARTED:
                        self.update_message(
                            "SYSTEM", "<<< INFO >>> Waiting for server to stop")
                        sleep(5)
                    else:
                        self.update_message(
                            "SYSTEM", "<<< INFO >>> Server stopped :)")

                self.get_available_models()

        except Exception as exc:
            self.update_message(
                "SYSTEM", f"<<< ERROR >>> Error creating server: {exc}")

        self.SERVER_MESSAGE.config(text='server UP' if self.SERVER_STARTED else 'server DOWN',
                                   foreground='green' if self.SERVER_STARTED else 'red')

    def send_message(self, e):
        # TODO: check server is actually started or stopped for second window chat
        other_server = GUI.is_server_started()
        if self.SERVER_STARTED or other_server:
            text = e.widget.get('0.0', 'end')
            self.update_message("USER", text)
            e.widget.delete('0.0', 'end')

            # XXX install locally with `pip install -e . -C cmake_args="-DLLAMA_METAL=on"`
            # call the chat in quick question (-qq) mode so it finishes after replying and only returns the result generated text
            # WARNING: it does not retain any context in between calls
            self.CHAT_PROCESS = Popen(
                f'''source venv/bin/activate;
                ilab chat -qq -gm "$(cat << EOF
                {text.replace('"', "'")}
                EOF
                )"''',
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                shell=True
            )

            # TODO: streaming mode for printing the info on screen
            # TODO: scroll to bottom
            stdout, stderr = self.CHAT_PROCESS.communicate()
            self.update_message("ILAB", stdout.decode('utf-8'))

            print(stdout.decode('utf-8'), stderr.decode('utf-8'))
        else:
            self.update_message(
                "SYSTEM", "<<< WARNING >>> Start the LLM server first")

    def show_chat(self):
        if self.CHAT_PANEL is None:
            self.CHAT_PANEL = tk.PanedWindow()
            self.TEXT_BOX = tk.Text(
                self.CHAT_PANEL,
                height=50,
                width=150
            )
            self.TEXT_BOX.grid(row=0, rowspan=3, sticky=tk.EW)
            self.TEXT_BOX.config(state='disabled')
            # self.CHAT_PANEL.add(self.TEXT_BOX)

            self.update_message('ILAB', "Hello! Ask me anything!")

            user_entry = tk.Text(self.CHAT_PANEL, width=150, height=10)
            user_entry.grid(row=3, rowspan=3, sticky=tk.EW)

            # send with SHIFT+ENTER
            user_entry.bind("<Shift-Return>", self.send_message)
            # new line with ENTER
            user_entry.bind(
                "<Return>", lambda x: self.TEXT_BOX.insert('end', '\n'))

            tk.Label(self.CHAT_PANEL, text="'Shift+Enter' to send. TO-DO button").grid(
                row=4, rowspan=3, sticky=tk.NE)

            self.CHAT_PANEL.pack()
        else:
            self.CHAT_PANEL.destroy()
            self.CHAT_PANEL = None

    def main(self):

        selection_panel = tk.PanedWindow()
        chat_button = ttk.Button(
            selection_panel,
            text="Chat", command=self.show_chat)
        chat_button.grid(row=0, column=0, sticky=tk.E)

        train_button = ttk.Button(
            selection_panel,
            text="Train", command=lambda x: print("todo"))
        train_button.grid(row=0, column=1, sticky=tk.W)
        selection_panel.pack()

        start_stop_server_button = ttk.Button(
            text="Start/Stop server", command=self.toggle_server)
        start_stop_server_button.place(relx=0.1, rely=0.96)

        # datatype of menu text
        self.SELECTED_MODEL = tk.StringVar()

        # initial menu text
        self.SELECTED_MODEL.set("DEFAULT")
        drop = tk.OptionMenu(self.WINDOW, self.SELECTED_MODEL, *self.MODELS)
        drop.place(relx=0.26, rely=0.962)

        self.show_chat()

        self.WINDOW.after(1000, self.init_lab)

        # kill all the process on window close -> server could be still up otherwise
        self.WINDOW.protocol("WM_DELETE_WINDOW", self.kill_server)

        # keep as last line of function to render the window
        self.WINDOW.mainloop()
