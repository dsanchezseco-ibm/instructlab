# native
from threading import Thread
from subprocess import Popen, PIPE
from time import sleep
import urllib.request

# First Party
import instructlab.lab as lab
import instructlab.config as config

# Third-party
import tkinter as tk
from tkinter import ttk


GEOMETRY_W = 1000
GEOMETRY_H = 800


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
        self.SERVER_THREAD = None

        self.SERVER_MESSAGE = ttk.Label(
            text='server UP' if self.SERVER_STARTED else 'server DOWN', foreground='green' if self.SERVER_STARTED else 'red')
        self.SERVER_MESSAGE.place(relx=0.01, rely=0.97)

        self.TEXT_BOX = None
        self.CHAT_PROCESS = None

    def update_message(self, role, text):
        message = text
        if role == 'ILAB':
            message = "ILAB >>> " + message + "\n---------\n\n"
        elif role == 'USER':
            message = "USER >>> " + message + "\n"
        else: # assume system
            message = "#### SYSTEM ####\n" + message +"\n################\n"

        self.TEXT_BOX.config(state='normal')
        self.TEXT_BOX.insert('end', '\n'+message)
        self.TEXT_BOX.config(state='disabled')

    def init_lab(self):
        lab.init(["--non-interactive"], standalone_mode=False,
                 obj=self.LAB, default_map=self.DEFAULT_MAP)
        self.update_message("SYSTEM", "<<< INFO >>> ILAB initiated, downloading model....")
        lab.download([], standalone_mode=False)
        self.update_message("SYSTEM", "<<< INFO >>> Model downloaded correctly :)")


    def toggle_server(self):
        # TODO: select model to start the server
        try:
            # start server with lab
            if not self.SERVER_STARTED:
                self.update_message("SYSTEM", "<<< INFO >>> Starting the server...")
                self.SERVER_THREAD = Thread(
                    target=lab.serve,
                    args=[
                        [
                            "--model-path", self.DEFAULT_MAP['serve']['model_path'],
                            "--gpu-layers", self.DEFAULT_MAP['serve']['gpu_layers'],
                            "--max-ctx-size", self.DEFAULT_MAP['serve']['max_ctx_size']
                        ],
                    ],
                    kwargs={
                        'standalone_mode': True,
                        'obj': self.LAB,
                        'default_map': self.DEFAULT_MAP
                    }
                )
                self.SERVER_THREAD.start()

                while not self.SERVER_STARTED:
                    #using default local server
                    status = None
                    try:
                        status = urllib.request.urlopen("http://localhost:8000").status
                    except:
                        print("server not ready yet")
                    if status  == 200:
                        # TODO: check correctly started
                        self.SERVER_STARTED = True
                        self.update_message("SYSTEM", "<<< INFO >>> Server started correctly :)")
                    else:
                        self.update_message("SYSTEM", "<<< INFO >>> Waiting for server to start...")
                        sleep(5)
        # TODO: stop server
            # else:
            #     self.update_message("SYSTEM", "<<< INFO >>> Shutting down the server...")
            #     #XXX: HOW??
            #     while self.SERVER_STARTED:
            #         #using default local server
            #         status = None
            #         try:
            #             status = urllib.request.urlopen("http://localhost:8000").status
            #         except:
            #             self.SERVER_STARTED = False
            #         if status == 200:
            #             self.update_message("SYSTEM", "<<< INFO >>> Waiting for server to stop...")
            #             sleep(5)
            #     self.update_message("SYSTEM", "<<< INFO >>> Server stopped")

        except Exception as exc:
            self.update_message("SYSTEM", f"<<< ERROR >>> Error creating server: {exc}")

        self.SERVER_MESSAGE.config(text='server UP' if self.SERVER_STARTED else 'server DOWN',
                                   foreground='green' if self.SERVER_STARTED else 'red')

    def send_message(self, e):
        if self.SERVER_STARTED:
            text = e.widget.get()
            self.update_message("USER", text)
            e.widget.delete(0, 'end')

            #XXX install locally with `pip install -e . -C cmake_args="-DLLAMA_METAL=on"`
            # call the chat in quick question (-qq) mode so it finishes after replying and only returns the result generated text
            # WARNING: it does not retain any context in between calls
            self.CHAT_PROCESS = Popen(f"source venv/bin/activate; ilab chat -qq {text}", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)

            stdout, stderr = self.CHAT_PROCESS.communicate()
            self.update_message("ILAB", stdout.decode('utf-8'))

            print(stdout.decode('utf-8'), stderr.decode('utf-8'))
        else:
            self.update_message("SYSTEM", "<<< WARNING >>> Start the LLM server first")

    def show_chat(self):
        self.TEXT_BOX = tk.Text(
            height=50,
            width=150
        )
        self.TEXT_BOX.pack()
        self.TEXT_BOX.config(state='disabled')

        self.update_message('ILAB', "Hello! Ask me anything!")

        user_entry = ttk.Entry(width=100)
        user_entry.pack()
        user_entry.bind("<Return>", self.send_message)

    def main(self):

        start_stop_server_button = ttk.Button(
            text="Start server" if not self.SERVER_STARTED else "Stop server", command=self.toggle_server)
        start_stop_server_button.place(relx=0.1, rely=0.96)

        self.show_chat()

        self.WINDOW.after(1000, self.init_lab)

        # keep as last line of function to render the window
        self.WINDOW.mainloop()
