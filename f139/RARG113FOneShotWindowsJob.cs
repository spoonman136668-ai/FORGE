// RAR-G113F: explicitly invoked, bounded Windows one-shot Job Object probe.
// G113G's independently authorized one-shot ran once and failed closed. This
// G113H source-only diagnostic patch grants no second execution authority.
// Never invoke from any F139 owner/controller path or automatic science workflow.
// This program is an inert standalone CLI unless --run-one-shot-offline is given.
// Child is the fixed local Windows system cmd.exe executing "exit 0"; never a
// model, training workload, shell-supplied expression, or user-defined binary.
// Kernel counters are OS diagnostics; commit peak is NOT physical tree RSS.
using System;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

public static class RARG113FOneShotWindowsJob
{
    private const uint CREATE_SUSPENDED = 0x00000004;
    private const uint CREATE_NO_WINDOW = 0x08000000;
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private const uint JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800;
    private const uint JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000;
    private const uint WAIT_OBJECT_0 = 0;
    private const int JobObjectBasicAccountingInformation = 1;
    private const int JobObjectExtendedLimitInformation = 9;
    private const int TimeoutMilliseconds = 10000;

    [StructLayout(LayoutKind.Sequential)]
    private struct STARTUPINFO
    {
        public uint cb;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpReserved;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpDesktop;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpTitle;
        public uint dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public ushort wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PROCESS_INFORMATION
    {
        public IntPtr hProcess, hThread;
        public uint dwProcessId, dwThreadId;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public IntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IO_COUNTERS
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct EXTENDED_LIMIT_INFORMATION
    {
        public BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public IntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct BASIC_ACCOUNTING
    {
        public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
    }

    [DllImport("kernel32.dll", EntryPoint = "CreateJobObjectW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObject(IntPtr attributes, string name);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetInformationJobObject(IntPtr job, int informationClass,
        ref EXTENDED_LIMIT_INFORMATION limits, uint length);

    [DllImport("kernel32.dll", EntryPoint = "CreateProcessW", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateProcess(string executable, StringBuilder commandLine,
        IntPtr processAttributes, IntPtr threadAttributes,
        [MarshalAs(UnmanagedType.Bool)] bool inheritHandles, uint creationFlags,
        IntPtr environment, string directory, ref STARTUPINFO startup, out PROCESS_INFORMATION info);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint ResumeThread(IntPtr thread);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool QueryInformationJobObject(IntPtr job, int informationClass,
        IntPtr record, uint length, out uint returnedLength);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetExitCodeProcess(IntPtr process, out uint code);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool TerminateProcess(IntPtr process, uint code);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);

    private static void Require(bool condition, string marker)
    {
        if (!condition) throw new Win32Exception(Marshal.GetLastWin32Error(), marker);
    }

    private static void Close(ref IntPtr handle)
    {
        if (handle != IntPtr.Zero && handle != new IntPtr(-1))
        {
            CloseHandle(handle);
            handle = IntPtr.Zero;
        }
    }

    private static T Query<T>(IntPtr job, int kind) where T : struct
    {
        var bytes = Marshal.SizeOf(typeof(T));
        IntPtr buffer = Marshal.AllocHGlobal(bytes);
        try
        {
            uint returned;
            Require(QueryInformationJobObject(job, kind, buffer, (uint)bytes, out returned),
                "RAR_G113F_JOB_READBACK_FAILED");
            if (returned != (uint)bytes)
                throw new InvalidOperationException("RAR_G113F_NATIVE_RECORD_SIZE_MISMATCH");
            return (T)Marshal.PtrToStructure(buffer, typeof(T));
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    private static string FixedNoOpExecutable()
    {
        string systemDirectory = Environment.SystemDirectory;
        if (String.IsNullOrWhiteSpace(systemDirectory))
            throw new InvalidOperationException("RAR_G113F_WINDOWS_SYSTEM_DIRECTORY_UNAVAILABLE");
        string child = Path.Combine(systemDirectory, "cmd.exe");
        if (!File.Exists(child))
            throw new InvalidOperationException("RAR_G113F_FIXED_CHILD_MISSING");
        return child;
    }

    private static void Probe()
    {
        if (Environment.OSVersion.Platform != PlatformID.Win32NT)
            throw new InvalidOperationException("RAR_G113F_WINDOWS_ONLY");
        IntPtr job = IntPtr.Zero;
        PROCESS_INFORMATION child = new PROCESS_INFORMATION();
        bool created = false, assigned = false;
        try
        {
            job = CreateJobObject(IntPtr.Zero, null); // fresh unnamed Job Object
            Require(job != IntPtr.Zero && job != new IntPtr(-1), "RAR_G113F_NEW_JOB_DENIED");
            var limits = new EXTENDED_LIMIT_INFORMATION();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            Require(SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                ref limits, (uint)Marshal.SizeOf(typeof(EXTENDED_LIMIT_INFORMATION))),
                "RAR_G113F_NO_KILL_ON_CLOSE");
            // Query the actually applied policy before creating any process.
            var applied = Query<EXTENDED_LIMIT_INFORMATION>(job, JobObjectExtendedLimitInformation);
            uint flags = applied.BasicLimitInformation.LimitFlags;
            if ((flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) == 0 ||
                (flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK)) != 0)
                throw new InvalidOperationException("RAR_G113F_UNSAFE_JOB_POLICY");

            string executable = FixedNoOpExecutable();
            var startup = new STARTUPINFO();
            startup.cb = (uint)Marshal.SizeOf(typeof(STARTUPINFO));
            // No inherited handles, no network, no arbitrary arguments, no model execution.
            Require(CreateProcess(executable,
                new StringBuilder("\"" + executable + "\" /d /q /c exit 0"),
                IntPtr.Zero, IntPtr.Zero, false, CREATE_SUSPENDED | CREATE_NO_WINDOW,
                IntPtr.Zero, Environment.SystemDirectory, ref startup, out child),
                "RAR_G113F_SUSPENDED_CHILD_DENIED");
            created = true;
            Require(AssignProcessToJobObject(job, child.hProcess),
                "RAR_G113F_ASSIGN_BEFORE_RESUME_DENIED");
            assigned = true;
            if (ResumeThread(child.hThread) == 0xFFFFFFFF)
                throw new InvalidOperationException("RAR_G113F_RESUME_FAILED");
            uint wait = WaitForSingleObject(child.hProcess, TimeoutMilliseconds);
            if (wait != WAIT_OBJECT_0)
                throw new InvalidOperationException("RAR_G113F_CHILD_TIMEOUT_OR_WAIT_FAILED");
            uint exitCode;
            Require(GetExitCodeProcess(child.hProcess, out exitCode),
                "RAR_G113F_EXIT_CODE_QUERY_FAILED");
            if (exitCode != 0)
                throw new InvalidOperationException("RAR_G113F_NOOP_EXIT_FAILED");

            // Read native counters while this code still owns the one-shot job handle.
            var accounting = Query<BASIC_ACCOUNTING>(job, JobObjectBasicAccountingInformation);
            var finalLimits = Query<EXTENDED_LIMIT_INFORMATION>(job, JobObjectExtendedLimitInformation);
            if (accounting.TotalProcesses != 1 || accounting.ActiveProcesses != 0 ||
                accounting.TotalUserTime < 0 || accounting.TotalKernelTime < 0 ||
                finalLimits.PeakJobMemoryUsed.ToInt64() < 0)
                throw new InvalidOperationException("RAR_G113F_NOT_SINGLE_PROCESS_QUIESCENT");
            if ((finalLimits.BasicLimitInformation.LimitFlags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) == 0)
                throw new InvalidOperationException("RAR_G113F_JOB_POLICY_DRIFT");

            long user100ns = accounting.TotalUserTime, kernel100ns = accounting.TotalKernelTime;
            if (user100ns > long.MaxValue - kernel100ns)
                throw new InvalidOperationException("RAR_G113F_COUNTER_OVERFLOW");
            // This is NOT a scientific receipt and has no authenticated external witness.
            Console.WriteLine(
                "RAR_G113F_NATIVE_OFFLINE_JOB_DIAGNOSTIC={\"schema\":\"rar.winjob-offline-probe.v1\"," +
                "\"classification\":\"NATIVE_FIXED_NOOP_UNWITNESSED_NOT_TRAINING_COST\"," +
                "\"fixed_child\":\"windows_system_cmd_exit_zero\",\"scope_created\":true," +
                "\"child_created_suspended\":true,\"assigned_before_resume\":true," +
                "\"child_process_exit_zero\":true,\"job_active_processes\":0,\"job_total_processes\":1," +
                "\"user_cpu_100ns\":" + user100ns.ToString(CultureInfo.InvariantCulture) +
                ",\"kernel_cpu_100ns\":" + kernel100ns.ToString(CultureInfo.InvariantCulture) +
                ",\"total_cpu_100ns\":" + (user100ns + kernel100ns).ToString(CultureInfo.InvariantCulture) +
                ",\"job_peak_memory_bytes_not_physical_rss\":" +
                  finalLimits.PeakJobMemoryUsed.ToInt64().ToString(CultureInfo.InvariantCulture) +
                ",\"memory_semantics\":\"JOB_PEAK_COMMIT_NOT_PHYSICAL_TREE_RSS\"," +
                "\"experiment_scope_authenticated_externally\":false," +
                "\"all_descendant_lifetimes_independently_witnessed\":false," +
                "\"native_training_cost_qualified\":false," +
                "\"scientific_first_use_authorized\":false," +
                "\"model_or_training_executed\":false," +
                "\"original_controller_changed\":false}");
        }
        finally
        {
            // An unassigned suspended child is not protected by job-close.
            if (created && !assigned) TerminateProcess(child.hProcess, 1);
            Close(ref child.hThread);
            Close(ref child.hProcess);
            // KILL_ON_JOB_CLOSE bounds any child/descendant still assigned to this job.
            Close(ref job);
        }
    }

    // Only fixed, source-declared markers may cross the diagnostic boundary.
    // Never output an exception message, OS text, stack, process path or secret.
    private static readonly string[] AllowedFailureMarkers = new string[]
    {
        "RAR_G113F_NEW_JOB_DENIED",
        "RAR_G113F_NO_KILL_ON_CLOSE",
        "RAR_G113F_JOB_READBACK_FAILED",
        "RAR_G113F_NATIVE_RECORD_SIZE_MISMATCH",
        "RAR_G113F_WINDOWS_SYSTEM_DIRECTORY_UNAVAILABLE",
        "RAR_G113F_FIXED_CHILD_MISSING",
        "RAR_G113F_WINDOWS_ONLY",
        "RAR_G113F_UNSAFE_JOB_POLICY",
        "RAR_G113F_SUSPENDED_CHILD_DENIED",
        "RAR_G113F_ASSIGN_BEFORE_RESUME_DENIED",
        "RAR_G113F_RESUME_FAILED",
        "RAR_G113F_CHILD_TIMEOUT_OR_WAIT_FAILED",
        "RAR_G113F_EXIT_CODE_QUERY_FAILED",
        "RAR_G113F_NOOP_EXIT_FAILED",
        "RAR_G113F_NOT_SINGLE_PROCESS_QUIESCENT",
        "RAR_G113F_JOB_POLICY_DRIFT",
        "RAR_G113F_COUNTER_OVERFLOW",
    };

    private static string BoundedFailureMarker(Exception exc)
    {
        if (!(exc is Win32Exception) && !(exc is InvalidOperationException))
            return "RAR_G113F_UNKNOWN_NATIVE_FAILURE";
        foreach (string marker in AllowedFailureMarkers)
            if (String.Equals(exc.Message, marker, StringComparison.Ordinal))
                return marker;
        return "RAR_G113F_UNCLASSIFIED_NATIVE_FAILURE";
    }

    public static int Main(string[] args)
    {
        // An explicit CLI gate is a safety interlock, NOT independent authority
        // for the operator or remote job to execute this native probe.
        if (args.Length != 1 || args[0] != "--run-one-shot-offline")
        {
            Console.Error.WriteLine("RAR_G113F_NOT_EXECUTED_EXPLICIT_ONE_SHOT_FLAG_REQUIRED");
            return 64;
        }
        try
        {
            Probe();
            return 0;
        }
        catch (Exception exc)
        {
            // Output one approved literal fault marker, never raw exception text.
            Console.Error.WriteLine("RAR_G113F_ABORTED:" + BoundedFailureMarker(exc));
            return 1;
        }
    }
}
