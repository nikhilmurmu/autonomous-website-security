@echo off
REM Run a WP-CLI command using the LocalWP site shell environment
cd /d "C:\Users\nikhi\Local Sites\autosec-test"
call "C:\Users\nikhi\AppData\Roaming\Local\lightning-services\php-8.2.29+0\bin\win64\php.exe" "C:\Users\nikhi\autonomous-website-security\wp-cli.phar" --path="C:\Users\nikhi\Local Sites\autosec-test\app\public" %*