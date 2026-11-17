# -*- coding: utf-8 -*-
"""
Cross-process coordination for guild and shard cache refreshes.

A System V semaphore (SEM_UNDO) limits the total number of concurrent
refreshes across all GuionBot processes. Per-resource flock locks prevent
the same guild or shard from being refreshed concurrently.

Lock files are persistent lock anchors, not status/ownership markers:
the kernel lock is automatically released when a process exits.
"""
import asyncio
import contextlib
import ctypes
import errno
import fcntl
import hashlib
import os

import golog


MAX_PARALLEL_LOADS = 2
_SEM_PROJECT_ID = ord("G")
_SEM_PERMISSIONS = 0o600
_SEM_UNDO = 0x1000
_IPC_CREAT = 0o1000
_IPC_EXCL = 0o2000
_SETVAL = 16

_libc = ctypes.CDLL(None, use_errno=True)


class _Sembuf(ctypes.Structure):
    _fields_ = [
        ("sem_num", ctypes.c_ushort),
        ("sem_op", ctypes.c_short),
        ("sem_flg", ctypes.c_short),
    ]


def _raise_errno(operation):
    error_number = ctypes.get_errno()
    raise OSError(error_number, operation + ": " + os.strerror(error_number))


def _get_semaphore_id():
    # ftok derives the same key in both processes from this shared module path.
    module_path = os.path.abspath(__file__).encode("utf-8")
    key = _libc.ftok(ctypes.c_char_p(module_path), ctypes.c_int(_SEM_PROJECT_ID))
    if key == -1:
        _raise_errno("ftok")

    cache_dir = os.path.join(os.getcwd(), "CACHE")
    os.makedirs(cache_dir, exist_ok=True)

    # Serialize first-time creation/initialization. This file is only an
    # initialization mutex; ongoing coordination is performed by the kernel.
    init_path = os.path.join(cache_dir, ".guild_semaphore_init.lock")
    fd = os.open(init_path, os.O_CREAT | os.O_RDWR, _SEM_PERMISSIONS)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        semid = _libc.semget(
            ctypes.c_int(key), ctypes.c_int(1),
            ctypes.c_int(_IPC_CREAT | _IPC_EXCL | _SEM_PERMISSIONS)
        )
        if semid == -1:
            error_number = ctypes.get_errno()
            if error_number != errno.EEXIST:
                raise OSError(error_number, "semget: " + os.strerror(error_number))
            semid = _libc.semget(
                ctypes.c_int(key), ctypes.c_int(1),
                ctypes.c_int(_IPC_CREAT | _SEM_PERMISSIONS)
            )
            if semid == -1:
                _raise_errno("semget existing semaphore")
        else:
            if _libc.semctl(
                ctypes.c_int(semid), ctypes.c_int(0), ctypes.c_int(_SETVAL),
                ctypes.c_int(MAX_PARALLEL_LOADS)
            ) == -1:
                _raise_errno("semctl SETVAL")
        return semid
    finally:
        os.close(fd)


def _sem_change(operation):
    semid = _get_semaphore_id()
    change = _Sembuf(0, operation, _SEM_UNDO)
    while True:
        if _libc.semop(ctypes.c_int(semid), ctypes.byref(change), ctypes.c_size_t(1)) == 0:
            return
        error_number = ctypes.get_errno()
        if error_number == errno.EINTR:
            continue
        raise OSError(error_number, "semop: " + os.strerror(error_number))


def _resource_lock_path(resource_key):
    digest = hashlib.sha256(str(resource_key).encode("utf-8")).hexdigest()
    lock_dir = os.path.join(os.getcwd(), "CACHE", "resource_locks")
    os.makedirs(lock_dir, exist_ok=True)
    return os.path.join(lock_dir, digest + ".lock")


def _acquire_resource_lock(resource_key):
    path = _resource_lock_path(resource_key)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, _SEM_PERMISSIONS)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    except Exception:
        os.close(fd)
        raise


def _release_resource_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


async def _acquire_cancellable(acquire_func, release_func):
    # asyncio cancellation cannot stop a blocking syscall in a worker thread.
    # If cancellation happens while waiting, wait for acquisition to complete
    # and immediately release it so no permit/lock is leaked.
    task = asyncio.create_task(asyncio.to_thread(acquire_func))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        acquired = await task
        await asyncio.to_thread(release_func, acquired)
        raise


@contextlib.asynccontextmanager
async def guild_loading(resource_key):
    """
    Acquire the per-guild/per-shard lock, then one of two global permits.

    resource_key must be stable across processes, e.g. 'guild:<id>' or
    'shard:<type>:<id>'.
    """
    lock_fd = await _acquire_cancellable(
        lambda: _acquire_resource_lock(resource_key),
        _release_resource_lock
    )
    try:
        golog.log("INFO", "Waiting for a shared guild/shard loading permit: "+str(resource_key))
        await _acquire_cancellable(
            lambda: _sem_change(-1),
            lambda _unused: _sem_change(1)
        )
        try:
            golog.log("INFO", "Acquired shared loading permit: "+str(resource_key))
            yield
        finally:
            await asyncio.to_thread(_sem_change, 1)
            golog.log("INFO", "Released shared loading permit: "+str(resource_key))
    finally:
        await asyncio.to_thread(_release_resource_lock, lock_fd)
