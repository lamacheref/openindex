openindex-api  |     return _bootstrap._gcd_import(name[level:], package, level)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1126, in _find_and_load_unlocked
openindex-api  |   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1140, in _find_and_load_unlocked
openindex-api  | ModuleNotFoundError: No module named 'src.api'
openindex-api  |   File "/usr/local/lib/python3.11/multiprocessing/process.py", line 314, in _bootstrap
openindex-api  |     self.run()
openindex-api  |   File "/usr/local/lib/python3.11/multiprocessing/process.py", line 108, in run
openindex-api  |     self._target(*self._args, **self._kwargs)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/_subprocess.py", line 80, in subprocess_started
openindex-api  |     target(sockets=sockets)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/supervisors/multiprocess.py", line 64, in target
openindex-api  |     return self.real_target(sockets)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 75, in run
openindex-api  |     return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/_compat.py", line 30, in asyncio_run
openindex-api  |     return runner.run(main)
openindex-api  |            ^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
openindex-api  |     return self._loop.run_until_complete(task)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
openindex-api  |     return future.result()
openindex-api  |            ^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 79, in serve
openindex-api  |     await self._serve(sockets)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 86, in _serve
openindex-api  |     config.load()
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/config.py", line 441, in load
openindex-api  |     self.loaded_app = import_from_string(self.app)
openindex-api  |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 22, in import_from_string
openindex-api  |     raise exc from None
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
openindex-api  |     module = importlib.import_module(module_str)
openindex-api  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/importlib/__init__.py", line 126, in import_module
openindex-api  |     return _bootstrap._gcd_import(name[level:], package, level)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1126, in _find_and_load_unlocked
openindex-api  |   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1140, in _find_and_load_unlocked
openindex-api  | ModuleNotFoundError: No module named 'src.api'
openindex-api  | Process SpawnProcess-194:
openindex-api  | Traceback (most recent call last):
openindex-api  |   File "/usr/local/lib/python3.11/multiprocessing/process.py", line 314, in _bootstrap
openindex-api  |     self.run()
openindex-api  |   File "/usr/local/lib/python3.11/multiprocessing/process.py", line 108, in run
openindex-api  |     self._target(*self._args, **self._kwargs)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/_subprocess.py", line 80, in subprocess_started
openindex-api  |     target(sockets=sockets)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/supervisors/multiprocess.py", line 64, in target
openindex-api  |     return self.real_target(sockets)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 75, in run
openindex-api  |     return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/_compat.py", line 30, in asyncio_run
openindex-api  |     return runner.run(main)
openindex-api  |            ^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
openindex-api  |     return self._loop.run_until_complete(task)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
openindex-api  |     return future.result()
openindex-api  |            ^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 79, in serve
openindex-api  |     await self._serve(sockets)
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/server.py", line 86, in _serve
openindex-api  |     config.load()
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/config.py", line 441, in load
openindex-api  |     self.loaded_app = import_from_string(self.app)
openindex-api  |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 22, in import_from_string
openindex-api  |     raise exc from None
openindex-api  |   File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
openindex-api  |     module = importlib.import_module(module_str)
openindex-api  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "/usr/local/lib/python3.11/importlib/__init__.py", line 126, in import_module
openindex-api  |     return _bootstrap._gcd_import(name[level:], package, level)
openindex-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1126, in _find_and_load_unlocked
openindex-api  |   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
openindex-api  |   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
openindex-api  |   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
openindex-api  |   File "<frozen importlib._bootstrap>", line 1140, in _find_and_load_unlocked
openindex-api  | ModuleNotFoundError: No module named 'src.api'
