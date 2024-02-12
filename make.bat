@echo off

REM �x�����ϐ��̗L����
setlocal enabledelayedexpansion

REM ���o�̓f�B���N�g���p�X
set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input\
set OUTPUT_DIR=%SCRIPT_DIR%output\
set LOG_DIR=%SCRIPT_DIR%log\

REM ���ʏo�͐�f�B���N�g���E���O�o�͐�f�B���N�g�����쐬
md "%OUTPUT_DIR%" > NUL 2>&1
md "%LOG_DIR%" > NUL 2>&1

REM Python �Ŏg�p���镶���R�[�h�� UTF-8 �Ɏw��
set PYTHONUTF8=1

REM ���͌��f�B���N�g���̊e�t�@�C�������ɏ���
for /f "usebackq tokens=*" %%f in (`dir /b "%INPUT_DIR%"`) do (
	set BASENAME=%%~nf

	REM �c�ƃL���h�̍Œ��H
	python solve.py -0 -l "%LOG_DIR%!BASENAME!_dist0.log" < "%INPUT_DIR%%%f" > "%OUTPUT_DIR%!BASENAME!_dist0.dat"

	REM �^���v�Z�L���h�̍Œ��H
	python solve.py -1 -l "%LOG_DIR%!BASENAME!_dist1.log" < "%INPUT_DIR%%%f" > "%OUTPUT_DIR%!BASENAME!_dist1.dat"

	REM ����\�̒��h�̍Œ��H (���K��69���̐���͏��O����)
	python -c "import sys, re; [print(re.sub(r'[-+]�K69_[^,#\t\r\n]+,?', '', line), end='') for line in sys.stdin]" < "%INPUT_DIR%%%f" ^
	| python solve.py -2 -l "%LOG_DIR%!BASENAME!_dist2.log" > "%OUTPUT_DIR%!BASENAME!_dist2.dat"
)

