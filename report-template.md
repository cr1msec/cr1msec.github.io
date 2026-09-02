---
title: MachineName
difficulty: Medium
tags: HTB, Web, SQLi, Linux PrivEsc
summary: One or two sentence summary of how the box was rooted — shown at the top of the page.
---

<!--
APPROVED TAGS — pick 2-4 that actually apply, don't invent new ones:

Access / Exploitation:
  Web, SQLi, SSTI, SSRF, LFI, RFI, File Upload, Command Injection,
  RCE, Authentication, Brute Force

Privilege Escalation:
  Linux PrivEsc, Windows PrivEsc, Sudo, SUID, Capabilities, Cron,
  Kernel Exploit, Service Exploit, Credential Abuse

Other:
  FTP, SSH, WordPress, Active Directory, SMB, API, Enumeration,
  Misconfiguration

(the script will warn you in the terminal if a tag isn't on this list)
-->

## Recon
Started with a basic Nmap scan:
```bash
nmap -sC -sV -Pn 10.129.x.x
```

Open ports:
|Port|Service|
|---|---|
|22|SSH|
|80|HTTP|

Description of what you found in this stage.

## Enumeration
More detail here. Use `inline code` for filenames, paths, commands.

```bash
ffuf -u http://target/FUZZ -w wordlist.txt
```

## Initial Access
```text
some raw output or credentials here
username : **SuperSecretPassword123**
```

Explanation of how you got the shell.

## Privilege Escalation
```bash
sudo -l
```
```text
output showing the vulnerable path
```

## Root
How you got root — the actual final step.

## Key Takeaways
- First lesson learned
- Second lesson learned
- Third lesson learned
