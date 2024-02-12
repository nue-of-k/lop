@echo off

REM 遅延環境変数の有効化
setlocal enabledelayedexpansion

REM 入出力ディレクトリパス
set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input\
set OUTPUT_DIR=%SCRIPT_DIR%output\
set LOG_DIR=%SCRIPT_DIR%log\

REM 結果出力先ディレクトリ・ログ出力先ディレクトリを作成
md "%OUTPUT_DIR%" > NUL 2>&1
md "%LOG_DIR%" > NUL 2>&1

REM Python で使用する文字コードを UTF-8 に指定
set PYTHONUTF8=1

REM 入力元ディレクトリの各ファイルを順に処理
for /f "usebackq tokens=*" %%f in (`dir /b "%INPUT_DIR%"`) do (
	set BASENAME=%%~nf

	REM 営業キロ派の最長路
	python solve.py -0 -l "%LOG_DIR%!BASENAME!_dist0.log" < "%INPUT_DIR%%%f" > "%OUTPUT_DIR%!BASENAME!_dist0.dat"

	REM 運賃計算キロ派の最長路
	python solve.py -1 -l "%LOG_DIR%!BASENAME!_dist1.log" < "%INPUT_DIR%%%f" > "%OUTPUT_DIR%!BASENAME!_dist1.dat"

	REM 実乗可能粁程派の最長路 (旅規第69条の制約は除外する)
	python -c "import sys, re; [print(re.sub(r'[-+]規69_[^,#\t\r\n]+,?', '', line), end='') for line in sys.stdin]" < "%INPUT_DIR%%%f" ^
	| python solve.py -2 -l "%LOG_DIR%!BASENAME!_dist2.log" > "%OUTPUT_DIR%!BASENAME!_dist2.dat"
)

