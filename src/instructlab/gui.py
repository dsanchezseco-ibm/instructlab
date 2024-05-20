# native
from threading import Thread
from subprocess import Popen, PIPE
from time import sleep

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
        # self.LAB = lab.Lab(config.read_config(config.DEFAULT_CONFIG))
        self.LAB = lab.Lab(config.get_default_config())
        self.DEFAULT_MAP = config.get_dict(self.LAB.config)
        self.SERVER_STARTED = False

        self.STATUS_MESSAGE = ttk.Label(
            text="Initiating ILAB, please standby...")
        self.STATUS_MESSAGE.place(relx=0.01, rely=0.93)

        self.SERVER_MESSAGE = ttk.Label(
            text='server UP' if self.SERVER_STARTED else 'server DOWN', foreground='green' if self.SERVER_STARTED else 'red')
        self.SERVER_MESSAGE.place(relx=0.01, rely=0.97)

        self.TEXT_BOX = None
        self.CHAT_PROCESS = None

    def init_lab(self, message):
        lab.init(["--non-interactive"], standalone_mode=False,
                 obj=self.LAB, default_map=self.DEFAULT_MAP)
        message.config(text='ILAB initiated')

        lab.download([], standalone_mode=False)
        message.config(text='model downloaded')

    def toggle_server(self):
        # TODO: stop server
        # TODO: select model to start the server
        # try:
        # start server with lab
        if not self.SERVER_STARTED:
            server_thread = Thread(
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
            server_thread.start()

            sleep(5)

            # TODO: check correctly started
            self.SERVER_STARTED = not self.SERVER_STARTED
            # except Exception as exc:
            #     self.STATUS_MESSAGE.config(text=f"Error creating server: {exc}", foreground="red")

        self.SERVER_MESSAGE.config(text='server UP' if self.SERVER_STARTED else 'server DOWN',
                                   foreground='green' if self.SERVER_STARTED else 'red')

    def update_message(self, message):
        self.TEXT_BOX.config(state='normal')
        self.TEXT_BOX.insert('end', '\n'+message)
        self.TEXT_BOX.config(state='disabled')

    def send_message(self, e):
        text = e.widget.get()
        self.update_message("USER >>> " +text)
        e.widget.delete(0, 'end')

        #XXX install locally with `pip install -e . -C cmake_args="-DLLAMA_METAL=on"`
        self.CHAT_PROCESS = Popen(f"source venv/bin/activate; ilab chat -c non_interactive -qq {text}", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)

        stdout, stderr = self.CHAT_PROCESS.communicate()
        self.update_message("ILAB >>> " +stdout.decode('utf-8') + "\n\n-------------")

        print(stdout.decode('utf-8'), stderr.decode('utf-8'))

    def show_chat(self):
        message = "ILAB >>> Ask me anything! \n-------------"
        self.TEXT_BOX = tk.Text(
            height=50,
            width=150
        )
        self.TEXT_BOX.pack()
        self.TEXT_BOX.insert('end', message)
        self.TEXT_BOX.config(state='disabled')

        user_entry = ttk.Entry(width=100)
        user_entry.pack()
        user_entry.bind("<Return>", self.send_message)

    def main(self):

        start_stop_server_button = ttk.Button(
            text="Start server" if not self.SERVER_STARTED else "Stop server", command=self.toggle_server)
        start_stop_server_button.place(relx=0.1, rely=0.96)

        self.show_chat()

        self.WINDOW.after(1000, self.init_lab, self.STATUS_MESSAGE)

        # keep as last line of function to render the window
        self.WINDOW.mainloop()
