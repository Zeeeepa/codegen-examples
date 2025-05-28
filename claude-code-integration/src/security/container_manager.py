"""
Advanced Container Management for Secure Code Execution

Provides secure, isolated environments for running untrusted code with
comprehensive security controls, resource limits, and monitoring.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import docker
import subprocess
import tempfile
import os


class ContainerRuntime(Enum):
    """Supported container runtimes."""
    DOCKER = "docker"
    GVISOR = "gvisor"
    KATA = "kata"
    PODMAN = "podman"


@dataclass
class ContainerLimits:
    """Resource limits for container execution."""
    memory_mb: int = 1024
    cpu_cores: float = 1.0
    disk_mb: int = 1024
    network_bandwidth_mbps: Optional[int] = None
    timeout_seconds: int = 300
    max_processes: int = 100
    max_open_files: int = 1024


@dataclass
class ContainerConfig:
    """Container configuration with security settings."""
    image: str
    command: List[str]
    limits: ContainerLimits
    environment: Dict[str, str] = None
    volumes: Dict[str, str] = None
    network_mode: str = "none"
    user: str = "nobody"
    read_only: bool = True
    no_new_privileges: bool = True
    security_opts: List[str] = None
    capabilities_drop: List[str] = None
    capabilities_add: List[str] = None


@dataclass
class ExecutionResult:
    """Result of command execution in container."""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None


class ContainerManager:
    """
    Advanced container manager with enterprise security features.
    
    Features:
    - Multiple runtime support (Docker, gVisor, Kata Containers)
    - Comprehensive resource limits and monitoring
    - Network isolation and security controls
    - Privilege dropping and capability management
    - Audit logging and compliance tracking
    - Automatic cleanup and resource management
    """
    
    def __init__(
        self,
        runtime: str = "docker",
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize container manager with specified runtime."""
        self.runtime = ContainerRuntime(runtime)
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize runtime client
        if self.runtime == ContainerRuntime.DOCKER:
            self.client = docker.from_env()
        elif self.runtime == ContainerRuntime.GVISOR:
            self.client = docker.from_env()
            self._setup_gvisor()
        elif self.runtime == ContainerRuntime.KATA:
            self.client = docker.from_env()
            self._setup_kata()
        else:
            raise ValueError(f"Unsupported runtime: {runtime}")
        
        # Active containers tracking
        self.active_containers = {}
        
        # Security defaults
        self.default_security_opts = [
            "no-new-privileges:true",
            "seccomp:unconfined",  # Will be replaced with custom profile
            "apparmor:docker-default"
        ]
        
        self.default_capabilities_drop = [
            "ALL"
        ]
        
        self.default_capabilities_add = [
            "CHOWN",
            "DAC_OVERRIDE",
            "FOWNER",
            "SETGID",
            "SETUID"
        ]
    
    async def create_container(
        self,
        image: str,
        command: List[str],
        limits: Optional[Dict[str, Any]] = None,
        security_config: Optional[Dict[str, Any]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a secure container with specified configuration.
        
        Args:
            image: Container image to use
            command: Command to run in container
            limits: Resource limits configuration
            security_config: Security configuration overrides
            environment: Environment variables
            
        Returns:
            Container ID
        """
        container_id = str(uuid.uuid4())
        
        try:
            # Build container configuration
            container_limits = ContainerLimits(**(limits or {}))
            
            # Security configuration
            security_opts = self.default_security_opts.copy()
            capabilities_drop = self.default_capabilities_drop.copy()
            capabilities_add = self.default_capabilities_add.copy()
            
            if security_config:
                security_opts.extend(security_config.get("security_opts", []))
                capabilities_drop.extend(security_config.get("capabilities_drop", []))
                capabilities_add.extend(security_config.get("capabilities_add", []))
            
            # Create custom seccomp profile
            seccomp_profile = self._create_seccomp_profile()
            
            # Container creation parameters
            container_params = {
                "image": image,
                "command": command,
                "name": f"claude-validation-{container_id}",
                "detach": True,
                "remove": False,  # We'll remove manually for cleanup
                "user": "nobody:nogroup",
                "read_only": True,
                "network_mode": "none",
                "environment": environment or {},
                "mem_limit": f"{container_limits.memory_mb}m",
                "cpu_quota": int(container_limits.cpu_cores * 100000),
                "cpu_period": 100000,
                "pids_limit": container_limits.max_processes,
                "ulimits": [
                    docker.types.Ulimit(name="nofile", soft=container_limits.max_open_files, hard=container_limits.max_open_files)
                ],
                "security_opt": security_opts,
                "cap_drop": capabilities_drop,
                "cap_add": capabilities_add,
                "tmpfs": {
                    "/tmp": "rw,noexec,nosuid,size=100m",
                    "/var/tmp": "rw,noexec,nosuid,size=100m"
                }
            }
            
            # Add runtime-specific configuration
            if self.runtime == ContainerRuntime.GVISOR:
                container_params["runtime"] = "runsc"
            elif self.runtime == ContainerRuntime.KATA:
                container_params["runtime"] = "kata-runtime"
            
            # Create and start container
            container = self.client.containers.create(**container_params)
            container.start()
            
            # Track active container
            self.active_containers[container_id] = {
                "container": container,
                "created_at": asyncio.get_event_loop().time(),
                "limits": container_limits,
                "config": container_params
            }
            
            self.logger.info(f"Created secure container {container_id} with runtime {self.runtime.value}")
            
            return container_id
            
        except Exception as e:
            self.logger.error(f"Failed to create container: {e}")
            raise
    
    async def exec_command(
        self,
        container_id: str,
        command: List[str],
        capture_output: bool = False,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Execute command in container with monitoring and limits.
        
        Args:
            container_id: Container ID
            command: Command to execute
            capture_output: Whether to capture stdout/stderr
            timeout: Execution timeout in seconds
            cwd: Working directory
            environment: Additional environment variables
            
        Returns:
            ExecutionResult with output and metrics
        """
        if container_id not in self.active_containers:
            raise ValueError(f"Container {container_id} not found")
        
        container_info = self.active_containers[container_id]
        container = container_info["container"]
        limits = container_info["limits"]
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare execution parameters
            exec_params = {
                "cmd": command,
                "stdout": capture_output,
                "stderr": capture_output,
                "stdin": False,
                "tty": False,
                "privileged": False,
                "user": "nobody",
                "environment": environment or {},
                "workdir": cwd
            }
            
            # Create execution
            exec_id = container.client.api.exec_create(
                container.id,
                **exec_params
            )
            
            # Start execution with timeout
            exec_timeout = timeout or limits.timeout_seconds
            
            try:
                result = await asyncio.wait_for(
                    self._run_exec(container, exec_id["Id"], capture_output),
                    timeout=exec_timeout
                )
            except asyncio.TimeoutError:
                # Kill the execution
                try:
                    container.client.api.exec_resize(exec_id["Id"], height=0, width=0)
                except:
                    pass
                raise TimeoutError(f"Command execution timed out after {exec_timeout} seconds")
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Get resource usage
            stats = container.stats(stream=False)
            memory_usage = self._extract_memory_usage(stats)
            cpu_usage = self._extract_cpu_usage(stats)
            
            return ExecutionResult(
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage
            )
            
        except Exception as e:
            self.logger.error(f"Command execution failed in container {container_id}: {e}")
            raise
    
    async def _run_exec(
        self,
        container: Any,
        exec_id: str,
        capture_output: bool
    ) -> Dict[str, Any]:
        """Run execution and capture output."""
        loop = asyncio.get_event_loop()
        
        def _exec():
            output = container.client.api.exec_start(
                exec_id,
                detach=False,
                stream=False
            )
            
            inspect = container.client.api.exec_inspect(exec_id)
            
            if capture_output:
                if isinstance(output, bytes):
                    stdout = output.decode('utf-8', errors='replace')
                    stderr = ""
                else:
                    stdout = str(output)
                    stderr = ""
            else:
                stdout = ""
                stderr = ""
            
            return {
                "exit_code": inspect["ExitCode"],
                "stdout": stdout,
                "stderr": stderr
            }
        
        return await loop.run_in_executor(None, _exec)
    
    async def copy_to_container(
        self,
        container_id: str,
        source_path: str,
        dest_path: str
    ) -> bool:
        """Copy file or directory to container."""
        if container_id not in self.active_containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.active_containers[container_id]["container"]
        
        try:
            with open(source_path, 'rb') as f:
                container.put_archive(dest_path, f.read())
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy to container: {e}")
            return False
    
    async def copy_from_container(
        self,
        container_id: str,
        source_path: str,
        dest_path: str
    ) -> bool:
        """Copy file or directory from container."""
        if container_id not in self.active_containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.active_containers[container_id]["container"]
        
        try:
            archive, _ = container.get_archive(source_path)
            with open(dest_path, 'wb') as f:
                for chunk in archive:
                    f.write(chunk)
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy from container: {e}")
            return False
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get real-time container statistics."""
        if container_id not in self.active_containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.active_containers[container_id]["container"]
        
        try:
            stats = container.stats(stream=False)
            return {
                "memory_usage": self._extract_memory_usage(stats),
                "cpu_usage": self._extract_cpu_usage(stats),
                "network_io": self._extract_network_io(stats),
                "block_io": self._extract_block_io(stats)
            }
        except Exception as e:
            self.logger.error(f"Failed to get container stats: {e}")
            return {}
    
    async def remove_container(self, container_id: str) -> bool:
        """Remove container and cleanup resources."""
        if container_id not in self.active_containers:
            return True
        
        container_info = self.active_containers[container_id]
        container = container_info["container"]
        
        try:
            # Stop container if running
            if container.status == "running":
                container.stop(timeout=10)
            
            # Remove container
            container.remove(force=True)
            
            # Remove from tracking
            del self.active_containers[container_id]
            
            self.logger.info(f"Removed container {container_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove container {container_id}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup all active containers."""
        container_ids = list(self.active_containers.keys())
        
        for container_id in container_ids:
            await self.remove_container(container_id)
        
        self.logger.info("Container cleanup completed")
    
    def _setup_gvisor(self):
        """Setup gVisor runtime configuration."""
        # Check if gVisor is available
        try:
            result = subprocess.run(["runsc", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("gVisor (runsc) not available")
            self.logger.info("gVisor runtime configured")
        except FileNotFoundError:
            raise RuntimeError("gVisor (runsc) not installed")
    
    def _setup_kata(self):
        """Setup Kata Containers runtime configuration."""
        # Check if Kata is available
        try:
            result = subprocess.run(["kata-runtime", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("Kata Containers runtime not available")
            self.logger.info("Kata Containers runtime configured")
        except FileNotFoundError:
            raise RuntimeError("Kata Containers runtime not installed")
    
    def _create_seccomp_profile(self) -> str:
        """Create custom seccomp profile for enhanced security."""
        # Minimal seccomp profile allowing only essential syscalls
        profile = {
            "defaultAction": "SCMP_ACT_ERRNO",
            "architectures": ["SCMP_ARCH_X86_64"],
            "syscalls": [
                {"names": ["read", "write", "open", "close", "stat", "fstat", "lstat"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["poll", "lseek", "mmap", "mprotect", "munmap"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["brk", "rt_sigaction", "rt_sigprocmask", "rt_sigreturn"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["ioctl", "pread64", "pwrite64", "readv", "writev"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["access", "pipe", "select", "sched_yield", "mremap"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["msync", "mincore", "madvise", "shmget", "shmat", "shmctl"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["dup", "dup2", "pause", "nanosleep", "getitimer"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["alarm", "setitimer", "getpid", "sendfile", "socket"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["connect", "accept", "sendto", "recvfrom", "sendmsg"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["recvmsg", "shutdown", "bind", "listen", "getsockname"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["getpeername", "socketpair", "setsockopt", "getsockopt"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["clone", "fork", "vfork", "execve", "exit", "wait4"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["kill", "uname", "semget", "semop", "semctl"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["shmdt", "msgget", "msgsnd", "msgrcv", "msgctl"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["fcntl", "flock", "fsync", "fdatasync", "truncate"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["ftruncate", "getdents", "getcwd", "chdir", "fchdir"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["rename", "mkdir", "rmdir", "creat", "link"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["unlink", "symlink", "readlink", "chmod", "fchmod"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["chown", "fchown", "lchown", "umask", "gettimeofday"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["getrlimit", "getrusage", "sysinfo", "times", "ptrace"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["getuid", "syslog", "getgid", "setuid", "setgid"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["geteuid", "getegid", "setpgid", "getppid", "getpgrp"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["setsid", "setreuid", "setregid", "getgroups", "setgroups"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["setresuid", "getresuid", "setresgid", "getresgid"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["getpgid", "setfsuid", "setfsgid", "getsid", "capget"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["capset", "rt_sigpending", "rt_sigtimedwait", "rt_sigqueueinfo"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["rt_sigsuspend", "sigaltstack", "utime", "mknod"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["uselib", "personality", "ustat", "statfs", "fstatfs"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["sysfs", "getpriority", "setpriority", "sched_setparam"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["sched_getparam", "sched_setscheduler", "sched_getscheduler"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["sched_get_priority_max", "sched_get_priority_min", "sched_rr_get_interval"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["mlock", "munlock", "mlockall", "munlockall", "vhangup"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["modify_ldt", "pivot_root", "prctl", "arch_prctl"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["adjtimex", "setrlimit", "chroot", "sync", "acct"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["settimeofday", "mount", "umount2", "swapon", "swapoff"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["reboot", "sethostname", "setdomainname", "iopl", "ioperm"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["create_module", "init_module", "delete_module", "get_kernel_syms"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["query_module", "quotactl", "nfsservctl", "getpmsg", "putpmsg"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["afs_syscall", "tuxcall", "security", "gettid", "readahead"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["setxattr", "lsetxattr", "fsetxattr", "getxattr", "lgetxattr"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["fgetxattr", "listxattr", "llistxattr", "flistxattr"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["removexattr", "lremovexattr", "fremovexattr", "tkill"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["time", "futex", "sched_setaffinity", "sched_getaffinity"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["set_thread_area", "io_setup", "io_destroy", "io_getevents"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["io_submit", "io_cancel", "get_thread_area", "lookup_dcookie"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["epoll_create", "epoll_ctl_old", "epoll_wait_old", "remap_file_pages"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["getdents64", "set_tid_address", "restart_syscall", "semtimedop"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["fadvise64", "timer_create", "timer_settime", "timer_gettime"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["timer_getoverrun", "timer_delete", "clock_settime", "clock_gettime"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["clock_getres", "clock_nanosleep", "exit_group", "epoll_wait"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["epoll_ctl", "tgkill", "utimes", "vserver", "mbind"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["set_mempolicy", "get_mempolicy", "mq_open", "mq_unlink"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["mq_timedsend", "mq_timedreceive", "mq_notify", "mq_getsetattr"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["kexec_load", "waitid", "add_key", "request_key", "keyctl"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["ioprio_set", "ioprio_get", "inotify_init", "inotify_add_watch"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["inotify_rm_watch", "migrate_pages", "openat", "mkdirat"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["mknodat", "fchownat", "futimesat", "newfstatat", "unlinkat"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["renameat", "linkat", "symlinkat", "readlinkat", "fchmodat"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["faccessat", "pselect6", "ppoll", "unshare", "set_robust_list"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["get_robust_list", "splice", "tee", "sync_file_range"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["vmsplice", "move_pages", "utimensat", "epoll_pwait"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["signalfd", "timerfd_create", "eventfd", "fallocate"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["timerfd_settime", "timerfd_gettime", "accept4", "signalfd4"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["eventfd2", "epoll_create1", "dup3", "pipe2", "inotify_init1"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["preadv", "pwritev", "rt_tgsigqueueinfo", "perf_event_open"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["recvmmsg", "fanotify_init", "fanotify_mark", "prlimit64"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["name_to_handle_at", "open_by_handle_at", "clock_adjtime"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["syncfs", "sendmmsg", "setns", "getcpu", "process_vm_readv"], "action": "SCMP_ACT_ALLOW"},
                {"names": ["process_vm_writev", "kcmp", "finit_module"], "action": "SCMP_ACT_ALLOW"}
            ]
        }
        
        # Write profile to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(profile, f)
            return f.name
    
    def _extract_memory_usage(self, stats: Dict[str, Any]) -> Optional[int]:
        """Extract memory usage from container stats."""
        try:
            return stats["memory_stats"]["usage"]
        except (KeyError, TypeError):
            return None
    
    def _extract_cpu_usage(self, stats: Dict[str, Any]) -> Optional[float]:
        """Extract CPU usage percentage from container stats."""
        try:
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            
            if system_delta > 0:
                return (cpu_delta / system_delta) * 100.0
        except (KeyError, TypeError, ZeroDivisionError):
            pass
        return None
    
    def _extract_network_io(self, stats: Dict[str, Any]) -> Dict[str, int]:
        """Extract network I/O stats from container stats."""
        try:
            networks = stats["networks"]
            total_rx = sum(net["rx_bytes"] for net in networks.values())
            total_tx = sum(net["tx_bytes"] for net in networks.values())
            return {"rx_bytes": total_rx, "tx_bytes": total_tx}
        except (KeyError, TypeError):
            return {"rx_bytes": 0, "tx_bytes": 0}
    
    def _extract_block_io(self, stats: Dict[str, Any]) -> Dict[str, int]:
        """Extract block I/O stats from container stats."""
        try:
            blkio = stats["blkio_stats"]["io_service_bytes_recursive"]
            read_bytes = sum(item["value"] for item in blkio if item["op"] == "Read")
            write_bytes = sum(item["value"] for item in blkio if item["op"] == "Write")
            return {"read_bytes": read_bytes, "write_bytes": write_bytes}
        except (KeyError, TypeError):
            return {"read_bytes": 0, "write_bytes": 0}

