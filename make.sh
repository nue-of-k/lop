#!/bin/bash

# 入出力ディレクトリパス
SCRIPT_DIR="$(cd "$(dirname $0)"; pwd)"
INPUT_DIR="${SCRIPT_DIR}/input"
OUTPUT_DIR="${SCRIPT_DIR}/output"
LOG_DIR="${SCRIPT_DIR}/log"

# 結果出力先ディレクトリ・ログ出力先ディレクトリを作成
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${LOG_DIR}"

# Python で使用する文字コードを UTF-8 に指定
export PYTHONUTF8=1

# 入力元ディレクトリの各ファイルを順に処理
for INPUT in "${INPUT_DIR}/"* ; do
	BASENAME="$(basename "${INPUT%.*}")"

	# 営業キロ派の最長路
	python solve.py -0 -l "${LOG_DIR}/${BASENAME}_dist0.log" < "${INPUT}" > "${OUTPUT_DIR}/${BASENAME}_dist0.dat"

	# 運賃計算キロ派の最長路
	python solve.py -1 -l "${LOG_DIR}/${BASENAME}_dist1.log" < "${INPUT}" > "${OUTPUT_DIR}/${BASENAME}_dist1.dat"

	# 実乗可能粁程派の最長路 (旅規第69条の制約は除外する)
	python -c "import sys, re; [print(re.sub(r'[-+]規69_[^,#\t\r\n]+,?', '', line), end='') for line in sys.stdin]" < "${INPUT}" |
	python solve.py -2 -l "${LOG_DIR}/${BASENAME}_dist2.log" > "${OUTPUT_DIR}/${BASENAME}_dist2.dat"
done

