<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Directory links on Windows

Some LATTICE tooling makes one directory appear in a second place. `mise run skills:link` puts each skill from `.claude/skills/` into `~/.copilot/skills/`, and [ADR-A117](../architecture/decisions/ADR-A117-agent-guidance-and-skill-library.md) suggests linking the private overlay folder to a private checkout. On macOS and Linux that is a symbolic link. Windows has three kinds of link and a fallback, and which of them a given machine allows depends on its edition, its settings, its policies and the volume. This page explains how each works, what can stop one being made, and how the tooling chooses.

## Four ways to make a directory appear twice

| | Symbolic link | Directory junction | Hard link | Copy |
|---|---|---|---|---|
| Points at | a file or a directory, by path | a directory, by path | the same file record on disk | nothing. It is a second set of files |
| Target on another local volume | yes | yes | no | not applicable |
| Target on a network share | yes, by UNC path | no | no | yes |
| Target stored as | a relative or an absolute path | an absolute path | not applicable | not applicable |
| Who may make one | a holder of the "Create symbolic links" right, Administrators by default, or anyone where Developer Mode is on | anyone who may create a directory where the link goes | anyone with write access to the volume | anyone |
| Follows changes to the source | yes | yes | yes, for that one file | no. Re-run the task after pulling |
| Nearest equivalent on Linux and macOS | `ln -s` | `ln -s` to a directory | `ln` | `cp -R` |

A hard link names a file, never a directory, and never one on another volume, so it cannot link a skill folder. That leaves a symbolic link, a junction or a copy.

## How a junction works

A junction is a *reparse point*. NTFS lets a file or directory carry a small block of data with a numeric *tag* naming what the data means. When Windows opens a path and meets a reparse point, it does not open the directory itself. It hands the tag and the data to whatever understands that tag, and if nothing does, the open fails. Windows itself understands the tag junctions use, `IO_REPARSE_TAG_MOUNT_POINT` (`0xA0000003`), which they share with mounted folders. Its data is the target path. Windows substitutes that path for the part of the path it has read so far, and carries on with the rest. A program that opens `~/.copilot/skills/lattice-design/SKILL.md` gets the file under `.claude/skills/lattice-design/`, and needs no knowledge of links to do so. That is why Copilot, Claude Code and a text editor all read through a junction as if it were the directory.

`fsutil reparsepoint query` on a junction this tooling made reports:

```text
Reparse Tag Value : 0xa0000003
Tag value: Microsoft
Tag value: Name Surrogate
```

*Microsoft* means the tag is one of Windows' own. *Name Surrogate* means the entry stands in for another named entry, which is how a careful program knows it is a link and must not walk into it when copying or deleting a tree.

Microsoft's documentation sets these limits on junctions and on reparse points in general:

- A junction links directories only, never a file.
- Its target must be on a local volume of the same computer. `C:\dirx` may link to `D:\diry`, but not to a mapped network drive such as `Z:\dir2`.
- A reparse point can only be set on an empty directory, so a junction is made as a new, empty directory that then receives its target.
- A path may pass through at most 63 reparse points, or 31 where they hold fully qualified targets, as a junction does.
- A file or directory may carry a reparse point or extended attributes, never both.
- The reparse data, target path included, is at most 16 KB.

Two more facts were observed on the machine this was written on:

- **A junction stores an absolute target**, even when `mklink /J` is given a relative one. `mklink /J rel target`, run in a scratch directory, stored `\\?\C:\Users\...\target`. Moving or renaming the checkout therefore leaves every junction pointing at the old place. Re-run `mise run skills:link` after moving a checkout.
- **A junction whose target is gone stays behind.** `Path.exists()` is false, since the target cannot be opened, while `Path.is_junction()` is still true. The tooling tests `is_junction()` before `exists()` for that reason, and removes such a junction like any other.

## Is a junction available everywhere

Junctions are a feature of NTFS and have been since Windows 2000, so every Windows client and server still in support can make them on an NTFS volume. A Windows 10 or 11 machine's system drive is NTFS.

A junction needs a volume that holds reparse points. FAT32 and exFAT, which are common on removable drives, hold none, so a checkout or a home directory on such a drive cannot have one. ReFS, used by Windows 11's Dev Drive, supports reparse points, but junctions on it were not tried for this page. A home directory redirected to a network share, which some organisations configure, may refuse to hold a junction too. In each of these cases the tooling falls back to a copy, as described below.

`mklink /J` has been a `cmd.exe` built-in since Windows Vista. The tooling does not need it, since Python can make a junction itself.

## Who may make one

The two kinds of link are governed differently, which is the reason the tooling tries both.

**A symbolic link needs a privilege.** Creating one needs `SeCreateSymbolicLinkPrivilege`, the "Create symbolic links" user right. Microsoft's default grants it to the Administrators group only, and a process holds it only when elevated. Without it, Windows refuses with error 1314, "A required privilege is not held by the client". Since Windows 10 version 1703, Developer Mode lets an account without the right create symbolic links, and Python asks for that when it makes one. Many managed machines keep Developer Mode off.

**A junction needs no privilege.** Windows checks only the ordinary NTFS permission to create a directory in the place the junction goes. A user may make one in their own profile, which is where `~/.copilot/skills` is. On the machine this was written on, Windows 11 Enterprise build 26200 under an unelevated account, a symbolic link was refused with error 1314 and a junction to the same directory was made.

## What a policy can do

An organisation can restrict links in several ways. None of them is certain to apply to a given machine, so the tooling tries the next kind of link, then a copy, rather than guessing in advance.

- **The "Create symbolic links" right.** It is assigned in Group Policy under User Rights Assignment. It governs symbolic links, not junctions.
- **Symbolic link evaluation.** `fsutil behavior query SymlinkEvaluation` shows which symbolic links Windows follows, in four classes: local to local, local to remote, remote to local and remote to remote. Group Policy can set them. Microsoft's documentation names symbolic links only. A junction is local to local by construction, and Windows enables that class by default. The machine this was written on reports both local classes enabled and both remote classes disabled, which are the defaults.
- **Redirection Guard.** Windows has a process mitigation, `ProcessRedirectionTrustPolicy`, which Microsoft calls RedirectionGuard. As understood here, a process that opts in will not follow a junction made by a user who is not an administrator. It applies to the programs that opt in, not to the machine. The programs that read skills are not known to opt in. This was not tested.
- **Security software.** Junctions made by ordinary users are a known step in privilege-escalation attacks on other software, so endpoint detection or application control may block or flag their creation. A refused junction raises an error, and the tooling copies instead.
- **No command prompt.** The Group Policy "Prevent access to the command prompt" can stop `cmd.exe` running. The tooling makes a junction with Python's `_winapi.CreateJunction`, which calls Windows directly, and runs `mklink /J` only on an interpreter that lacks it. `_winapi` is an internal CPython module, which CPython's own tests use to make junctions, so the tooling checks it is there rather than assuming so.

## How the tooling chooses

`tools/agent_guidance.py link`, run as `mise run skills:link`, makes each skill in this order and prints which it made:

1. **A symbolic link.** This is what macOS and Linux always make, and what Windows makes for an elevated process or with Developer Mode on.
2. **A directory junction**, when Windows refuses the symbolic link for lack of the privilege, error 1314. No other refusal is taken to mean a junction would work.
3. **A copy**, when neither link can be made for any reason, such as a volume that holds no reparse points or a policy that refuses one. The reason is printed. A copy holds a `.lattice-copy` file to mark it as this task's, and goes stale when the skills change. Re-run the task after pulling.

`--copy` makes copies on any platform. Running the task again replaces a link, junction or copy it made before, so a copy made while linking was refused becomes a link once it is allowed. It refuses to touch a directory it did not make.

The test `tools/test_agent_guidance.py` makes a link on whatever platform runs it and accepts a symbolic link or a junction. It also checks that a refused symbolic link becomes a junction, and that a skill which cannot be linked is copied and later linked again, on every platform, by refusing the link itself rather than skipping on Windows ([STD-323](standards.md)).

## Looking at a link

| To see | Run |
|---|---|
| every link in a directory, with its kind and target | `cmd /c dir /AL <directory>`, which lists a junction as `<JUNCTION>` |
| one link's kind and target in PowerShell | `Get-Item <link> \| Select-Object LinkType, Target` |
| the reparse tag and data | `fsutil reparsepoint query <link>` |
| the same from Python | `Path(link).is_junction()`, `Path(link).is_symlink()`, `os.readlink(link)` |

## Removing a link safely

Remove the link, never what it points at. On the machine this was written on, each of these removed a junction and left its target's files in place:

- `cmd /c rmdir <link>`
- `cmd /c rd /s /q <link>`
- `Remove-Item <link> -Recurse -Force` in Windows PowerShell 5.1
- `(Get-Item <link>).Delete()`
- `Path(link).unlink()` in Python

Python's `shutil.rmtree` refuses a junction outright, with "Cannot call rmtree on a symbolic link", and, given a tree that holds a junction, removes the junction without entering it.

Older versions of Windows Explorer and PowerShell are reported to have deleted a junction's target contents when deleting it recursively. The tooling never relies on a recursive delete being safe. `skills:link` and `tools/clean.py` test for a link or a junction first and unlink it. Do the same by hand: `rmdir <link>`, without `/s`, removes a junction or a directory symbolic link and fails on a real directory that is not empty, so it cannot remove more than the link.

## Sources

- Microsoft, [Hard links and junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions)
- Microsoft, [Reparse points](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points)
- Microsoft, [Creating symbolic links](https://learn.microsoft.com/en-us/windows/win32/fileio/creating-symbolic-links)
- Microsoft, [Create symbolic links](https://learn.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/create-symbolic-links), the user right and its defaults
- Microsoft, [fsutil behavior](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fsutil-behavior), for `symlinkevaluation`
- Microsoft, [PROCESS_MITIGATION_POLICY](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-process_mitigation_policy), which lists `ProcessRedirectionTrustPolicy`
- Python, [os.symlink](https://docs.python.org/3/library/os.html#os.symlink) on Developer Mode, and [Path.is_junction](https://docs.python.org/3/library/pathlib.html#pathlib.Path.is_junction)

The observations above were made on Windows 11 Enterprise build 26200, NTFS, Windows PowerShell 5.1 and Python 3.14, without elevation, on 2026-11-07.
