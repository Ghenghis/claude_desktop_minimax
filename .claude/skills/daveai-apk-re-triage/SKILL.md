---
name: daveai-apk-re-triage
description: Triage an Android APK for static analysis and extraction.
---

# daveai-apk-re-triage

**Use when:** faced with an APK, XAPK, or AAB that needs inspection

## Steps
- Hash the package and record package name, version, and target SDK.
- Decode with Apktool and inspect AndroidManifest.xml.
- Open in JADX for class/resource navigation.
- Identify native libraries and route to radare2 if needed.
- Produce RE_TRIAGE_REPORT.md with findings and next tool.

## Proof required
APK hash, decoded manifest excerpt, and chosen next lane
