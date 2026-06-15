@echo off
cd /d "%~dp0"
:: Ensure we are in the script's own directory
echo ----------------------------------------------------
echo Sending STOP signal to AeroForgeX...
echo ----------------------------------------------------

echo stop> run_control
:: Now run_control is placed in the expected location

echo.
echo Signal sent! 
echo The optimizer will shut down after the current 
echo iteration completes and save the results.
echo.
pause