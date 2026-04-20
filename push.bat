@echo off
cd /d "g:\다른 컴퓨터\SKKU 실험대\D\BIM LAB\취업준비-박사후연구원\성균관대학교\연구노트\lab-notebook"
git add -A
git commit -m "%~1"
git push origin main
echo.
echo Done.
pause
