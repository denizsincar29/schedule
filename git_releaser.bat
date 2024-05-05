@echo off
echo releasing to github
echo release notes taken from release.md
gh release create v%1 -F release.md dist/schedule.exe
echo done