// One bounded kernel wait for the EXISTING owner mutex file.
// No task, policy, database, scheduler, dispatch or retry operations.
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

public sealed class F139OriginalOwnerMutex : IDisposable
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Overlapped
    {
        public IntPtr Internal;
        public IntPtr InternalHigh;
        public uint Offset;
        public uint OffsetHigh;
        public IntPtr Event;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access,
        uint share, IntPtr security, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool LockFileEx(SafeFileHandle file, uint flags,
        uint reserved, uint low, uint high, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetOverlappedResultEx(SafeFileHandle file,
        IntPtr overlapped, out uint transferred, uint milliseconds,
        [MarshalAs(UnmanagedType.Bool)] bool alertable);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetOverlappedResult(SafeFileHandle file,
        IntPtr overlapped, out uint transferred,
        [MarshalAs(UnmanagedType.Bool)] bool wait);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CancelIoEx(SafeFileHandle file, IntPtr overlapped);

    private SafeFileHandle handle;
    private F139OriginalOwnerMutex(SafeFileHandle value) { handle = value; }

    public static F139OriginalOwnerMutex Acquire(string path, int milliseconds)
    {
        if (milliseconds < 1 || milliseconds > 900000)
            throw new ArgumentOutOfRangeException("milliseconds");
        if (String.IsNullOrEmpty(path) || !Path.IsPathRooted(path) ||
            !path.EndsWith(".lock", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("An existing absolute owner .lock path is required.");
        // OPEN_EXISTING; never create or write the mutex file. OVERLAPPED keeps
        // contention in the kernel, with a single cancellable bounded wait.
        SafeFileHandle file = CreateFileW(path, 0xC0000000, 3, IntPtr.Zero,
            3, 0x40000000, IntPtr.Zero);
        if (file.IsInvalid)
        {
            int error = Marshal.GetLastWin32Error();
            file.Dispose();
            throw new Win32Exception(error);
        }
        IntPtr memory = IntPtr.Zero;
        bool pending = false;
        bool completed = false;
        EventWaitHandle signal = null;
        try
        {
            signal = new EventWaitHandle(false, EventResetMode.ManualReset);
                memory = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlapped)));
                Overlapped request = new Overlapped();
                request.Event = signal.SafeWaitHandle.DangerousGetHandle();
                Marshal.StructureToPtr(request, memory, false);
                // Cover the legacy CRT descriptor position as well as byte zero.
                // Buffered Python seeks need not move that descriptor to zero.
                // LOCKFILE_EXCLUSIVE_LOCK only: do NOT fail immediately.
                if (!LockFileEx(file, 2, 0, 0xFFFFFFFF, 0x7FFFFFFF, memory))
                {
                    int error = Marshal.GetLastWin32Error();
                    if (error != 997) throw new Win32Exception(error);
                    pending = true;
                    uint transferred;
                    if (!GetOverlappedResultEx(file, memory, out transferred,
                        (uint)milliseconds, false))
                    {
                        error = Marshal.GetLastWin32Error();
                        if (error == 258)
                            throw new TimeoutException("F139_V36_OWNER_MUTEX_WAIT_EXPIRED_NO_MUTATION");
                        throw new Win32Exception(error);
                    }
                    completed = true;
                }
                F139OriginalOwnerMutex lease = new F139OriginalOwnerMutex(file);
                file = null;
                return lease;
        }
        finally
        {
                if (file != null)
                {
                    try
                    {
                        if (pending && !completed)
                        {
                            // Cancellation can race with a successful grant.
                            // Acknowledge completion before freeing OVERLAPPED;
                            // closing this handle also releases a racing grant.
                            CancelIoEx(file, memory);
                            uint ignored;
                            GetOverlappedResult(file, memory, out ignored, true);
                        }
                    }
                    finally { file.Dispose(); }
                }
                if (memory != IntPtr.Zero) Marshal.FreeHGlobal(memory);
                if (signal != null) signal.Dispose();
        }
    }

    public void Dispose()
    {
        // Closing the owning handle releases exactly its byte-range lock.
        // Idempotent, including exceptions after acquisition.
        SafeFileHandle owned = Interlocked.Exchange(ref handle, null);
        if (owned != null) owned.Dispose();
    }
}
