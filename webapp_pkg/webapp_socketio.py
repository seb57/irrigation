
from flask_socketio import SocketIO, emit, disconnect
from flask import session
from datetime import datetime
from threading import Lock
import os, sys
import stat

from webapp_pkg.Irrigationapp import msg_queue as IrrigationControllerAppConfig_msg_queue
from webapp_pkg.Irrigationapp import SCHEDULER_LOG_FILE as SCHEDULER_LOG_FILE

######################################################################################################################################################
# SOCKET IO
######################################################################################################################################################

class WEBAPPSOCKETIO(SocketIO):
   # pass
    thread = None
    thread_lock = Lock()
    msg_queue = []
    socketio = SocketIO()

    ## UPDATE THIS BASED ON render_template("wifi.html",pagename='wifi' ,
    open_pages ={'IrrigationControllerAppConfig': 0 , 'LogViewer' : 0 , 'LeakSensorAppConfig': 0 ,'wifi' : 0 }

    current_page = None
    debug =False
    def background_thread(self):
        old = None
        while True:
            self.socketio.emit('update_time' , {'txt' : datetime.now().strftime("%d %b %y %H:%M:%S")} , namespace='/test')

            if self.open_pages['IrrigationControllerAppConfig'] > 0 and os.path.exists(SCHEDULER_LOG_FILE) :
                if os.stat ( SCHEDULER_LOG_FILE ) [ stat.ST_MTIME ] != old:
                    old = os.stat ( SCHEDULER_LOG_FILE ) [ stat.ST_MTIME ]
                    f = open(SCHEDULER_LOG_FILE, "r")
                    self.socketio.emit('element_id_value_update' , {'id': 'logfiletext', 'value' :f.read()} , namespace='/test')

            while IrrigationControllerAppConfig_msg_queue and self.open_pages['IrrigationControllerAppConfig'] > 0 :
                msg = IrrigationControllerAppConfig_msg_queue.pop(0)
                if self.debug:
                    print ("Send this message " + str(msg))
                cmd = msg['cmd']
                del msg['cmd']
                self.socketio.emit(cmd , msg , namespace='/test')
            self.socketio.sleep(1)


    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socketio = SocketIO(*args, **kwargs)


        @self.socketio.on('connect', namespace='/test')
        def test_connect():
            if self.debug:
                print("new connect")
            with self.thread_lock:
                if self.thread is None:
                    self.thread = self.socketio.start_background_task(self.background_thread)


        # debug_socket_io =False

        @self.socketio.on('my_event', namespace='/test')
        def test_message(message):
            if self.debug:
                print (f'connect to : {message}')
            data = message['data']
            if data in self.open_pages:
                self.current_page = data
                self.open_pages[self.current_page] =  self.open_pages[self.current_page] +  1
            else:
                print(f'DEBUG: this pages is not yet defined in socketiot {message}')
           # session['receive_count'] = session.get('receive_count', 0) + 1
           # emit('my_response', {'data': message['data'], 'count': session['receive_count']})



        # @socketio.on('my_broadcast_event', namespace='/test')
        # def test_broadcast_message(self,message):
        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     emit('my_response',
        #         {'data': message['data'], 'count': session['receive_count']},
        #         broadcast=True)


        # @socketio.on('join', namespace='/test')
        # def join(self,message):
        #     join_room(message['room'])
        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     emit('my_response',
        #         {'data': 'In rooms: ' + ', '.join(rooms()),
        #         'count': session['receive_count']})


        @self.socketio.on('leave', namespace='/test')
        def leave(message):
            if self.debug:
                print(f'DEBUG: leave {message}')
        #     leave_room(message['room'])
        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     emit('my_response',
        #         {'data': 'In rooms: ' + ', '.join(rooms()),
        #         'count': session['receive_count']})


        @self.socketio.on('close_room', namespace='/test')
        def close(message):
            if self.debug:
                print(f'DEBUG: close {message}')
        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
        #                         'count': session['receive_count']},
        #         room=message['room'])
        #     close_room(message['room'])


        # @socketio.on('my_room_event', namespace='/test')
        # def send_room_message(self,message):
        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     emit('my_response',
        #         {'data': message['data'], 'count': session['receive_count']},
        #         room=message['room'])


        @self.socketio.on('disconnect_request', namespace='/test')
        def disconnect_request():
            if self.debug:
               print('DEBUG: disconnect_request')
        #     @copy_current_request_context
        #     def can_disconnect():
        #         disconnect()

        #     session['receive_count'] = session.get('receive_count', 0) + 1
        #     # for this emit we use a callback function
        #     # when the callback function is invoked we know that the message has been
        #     # received and it is safe to disconnect
        #     emit('my_response',
        #         {'data': 'Disconnected!', 'count': session['receive_count']},
        #         callback=can_disconnect)


        # @socketio.on('my_ping', namespace='/test')
        # def ping_pong(self):
        #     emit('my_pong')

        @self.socketio.on('disconnect', namespace='/test')
        def test_disconnect():
            if self.debug:
                print(f'DEBUG: test_disconnect')
            if self.current_page in self.open_pages:   
                self.open_pages[self.current_page] = self.open_pages[self.current_page] -1

        #     if debug_socket_io:
        #         print('Client disconnected', request.sid)
