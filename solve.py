import io
import sys
import argparse
import re
import pulp
from enum import Enum, auto



### 定数

LARGE_COEFF = 1000	# 十分大きな係数
DEFAULT_LOGFILE = 'pulp.log'	# 整数計画問題ソルバのログの出力先の既定値



### 標準入出力の文字コードとバッファリングの設定

sys.stdin  = io.TextIOWrapper(sys.stdin .buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True, write_through=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True, write_through=True)



### 枝の通過方向を表す列挙型
class Direction(Enum):
	DIRECTION_1_TO_2 = auto()
	DIRECTION_2_TO_1 = auto()



### 枝を表すクラス

class Edge:
	# 計算に用いる粁程
	#   0 : 営業キロ
	#   1 : 運賃計算キロ
	#   2 : 実乗可能粁程
	__using_weighted_distance = 0

	# コンストラクタ
	def __init__(self, company, line, station1, station2, distance, weighted, riding):
		self.__company = company
		self.__line = line
		self.__station1 = station1
		self.__station2 = station2
		self.__distance = distance
		self.__weighted = weighted
		self.__riding = riding
		self.__direction = Direction.DIRECTION_1_TO_2

	# 駅1
	@property
	def station1(self):
		return self.__station1

	# 駅2
	@property
	def station2(self):
		return self.__station2

	# 粁程
	@property
	def distance(self):
		if Edge.__using_weighted_distance == 0:
			return self.__distance
		elif Edge.__using_weighted_distance == 1:
			return self.__weighted
		elif Edge.__using_weighted_distance == 2:
			return self.__riding
		else:
			raise ValueError(__using_weighted_distance)

	# 通過方向の設定
	def __set_direction(self, value):
		self.__direction = value
	direction = property(fset=__set_direction)

	# 通過方向の変更
	def reverse(self):
		if self.__direction == Direction.DIRECTION_1_TO_2:
			self.__direction = Direction.DIRECTION_2_TO_1
		else:
			self.__direction = Direction.DIRECTION_1_TO_2
		return self

	# 経路の始点側の駅
	@property
	def station_s(self):
		if self.__direction == Direction.DIRECTION_1_TO_2:
			return self.__station1
		else:
			return self.__station2

	# 経路の終点側の駅
	@property
	def station_e(self):
		if self.__direction == Direction.DIRECTION_1_TO_2:
			return self.__station2
		else:
			return self.__station1

	# 出力用TSV
	@property
	def tsv(self):
		return '\t'.join([self.__company, self.__line, self.station_s, self.station_e, str(self.__distance), str(self.__weighted), str(self.__riding)])

	# 計算に用いる粁程の変更
	def using_weighted_distance(value):
		Edge.__using_weighted_distance = value


# 経路(枝のリスト)を逆順にする
def reverse_path(path):
	return list(map(lambda edge: edge.reverse(), path[::-1]))


# 経路(枝のリスト)の出力
def print_path(path, file=sys.stdout):
	for edge in path:
		print(edge.tsv, file=file)



### 問題の読込

# コマンドライン引数の解析
parser = argparse.ArgumentParser(description='最長片道切符問題ソルバ')
parser_group = parser.add_mutually_exclusive_group()
parser_group.add_argument('-0', dest='weighted_distance', action='store_const', const=0, help='計算に用いる粁程を営業キロとする (既定)')
parser_group.add_argument('-1', dest='weighted_distance', action='store_const', const=1, help='計算に用いる粁程を運賃計算キロとする')
parser_group.add_argument('-2', dest='weighted_distance', action='store_const', const=2, help='計算に用いる粁程を実乗可能粁程とする')
parser.add_argument('-l', dest='logfile', default=DEFAULT_LOGFILE, metavar='logfile', help='整数計画問題ソルバのログの出力先を logfile にする (既定値: {0})'.format(DEFAULT_LOGFILE))
parser.add_argument('-t', dest='threads', default=1, type=int, choices=range(1, 100), metavar='number', help='整数計画問題ソルバの使用する最大スレッド数を number にする (既定値: 1)')
args = parser.parse_args()
Edge.using_weighted_distance(args.weighted_distance or 0)


# 整数計画問題ソルバ (使いたいソルバに応じて書き換える)
solver = pulp.PULP_CBC_CMD(msg=False, threads=args.threads, gapRel=0, gapAbs=0, warmStart=False, logPath=args.logfile)
#solver = pulp.COIN_CMD(msg=False, threads=args.threads, gapRel=0, gapAbs=0, warmStart=False, logPath=args.logfile)
#solver = pulp.SCIP_CMD(msg=False, options=['-c', 'set numerics feastol 1e-10', '-c', 'set parallel maxnthreads {0}'.format(args.threads), '-l', args.logfile])


# 枝リストの読込
line_number = 0	# 行番号
edges = []	# 枝のリスト
vertices = {}	# 駅名から枝番号への連想配列
disj_groups = {}	# 選言制約
excl_groups = {}	# 排他制約
re_comment = re.compile(r'#.*$')	# コメントにマッチする正規表現
re_empty = re.compile(r'^\s*$')	# 空行にマッチする正規表現
for line in sys.stdin:
	line_number += 1

	# コメントの除去
	line = re_comment.sub('', line)

	# 空行の読み飛ばし
	if re_empty.match(line):
		continue

	# 行の解析
	parse = line.strip().split('\t')
	groups = parse[7].split(',') if len(parse) > 7 else []
	id = len(edges)
	edge = Edge(
		parse[0],
		parse[1],
		parse[2],
		parse[3],
		int(parse[4]),
		int(parse[5]),
		int(parse[6]),
	)
	edges.append(edge)

	# 自己閉路はエラー
	if parse[2] == parse[3]:
		print('Error: line {0}: 自己閉路があります'.format(line_number), file=sys.stderr)
		sys.exit(1)

	# 駅1に枝を追加
	if parse[2] in vertices:
		vertices[parse[2]].append(id)
	else:
		vertices[parse[2]] = [id]

	# 駅2に枝を追加
	if parse[3] in vertices:
		vertices[parse[3]].append(id)
	else:
		vertices[parse[3]] = [id]

	# 選言制約・排他制約
	for group in groups:
		if not group:
			pass
		elif group.startswith('+'):
			if group[1:] in disj_groups:
				disj_groups[group[1:]].append((id, True))
			else:
				disj_groups[group[1:]] = [(id, True)]
		elif group.startswith('-'):
			if group[1:] in disj_groups:
				disj_groups[group[1:]].append((id, False))
			else:
				disj_groups[group[1:]] = [(id, False)]
		elif group.startswith('*'):
			if group[1:] in excl_groups:
				excl_groups[group[1:]].append((id, LARGE_COEFF))
			else:
				excl_groups[group[1:]] = [(id, LARGE_COEFF)]
		elif group.startswith(':'):
			if group[1:] in excl_groups:
				excl_groups[group[1:]].append((id, 1))
			else:
				excl_groups[group[1:]] = [(id, 1)]
		else:
			raise ValueError(group)

# 入力が空であった場合は終了
if not edges:
	print('入力が空であるため終了します', file=sys.stderr)
	sys.exit(0)



### 整数計画問題の定義

problem = pulp.LpProblem('LOP', pulp.LpMaximize)


# 各枝 (v1, v2) に対し変数を3つずつ生成する
#   x[id] : 枝 (v1, v2) を経路の中間枝として通過する場合に1、そうでない場合0
#   y[id] : 駅 v1 を経路の始点(または終点)とし、最初(または最後)に枝 (v1, v2) を通る場合に1、そうでない場合0
#   z[id] : 駅 v2 を経路の始点(または終点)とし、最初(または最後)に枝 (v1, v2) を通る場合に1、そうでない場合0
x = pulp.LpVariable.dicts('x', (range(len(edges))), cat='Binary')
y = pulp.LpVariable.dicts('y', (range(len(edges))), cat='Binary')
z = pulp.LpVariable.dicts('z', (range(len(edges))), cat='Binary')


# 目的関数(最長経路の粁程)
expr = 0
for id in range(len(edges)):
	expr += (x[id] + y[id] + z[id]) * edges[id].distance
problem += expr


# 始点・終点を通るのは合わせて2回
expr = 0
for id in range(len(edges)):
	expr += y[id] + z[id]
problem += expr == 2


# 同一の枝は2回通らない
for id in range(len(edges)):
	problem += x[id] + y[id] + z[id] <= 1


# 各頂点を通るのは0回または2回
for vertex in vertices:
	# 頂点 vertex に接する枝に対応する変数のリスト
	variables = []
	for id in vertices[vertex]:
		variables.append(x[id])
		variables.append(y[id] if edges[id].station2 == vertex else z[id])

	# Σx <= 2
	expr = 0
	for var in variables:
		expr += var
	problem += expr <= 2

	# Σx >= 2x
	for var in variables:
		problem += expr >= 2 * var


# 選言制約
for group in disj_groups:
	expr = 0
	for cstrt in disj_groups[group]:
		if cstrt[1]:
			expr += x[cstrt[0]] + y[cstrt[0]] + z[cstrt[0]]
		else:
			expr += 1 - (x[cstrt[0]] + y[cstrt[0]] + z[cstrt[0]])
	problem += expr >= 1


# 排他制約
for group in excl_groups:
	expr = 0
	for cstrt in excl_groups[group]:
		expr += (x[cstrt[0]] + y[cstrt[0]] + z[cstrt[0]]) * cstrt[1]
	problem += expr <= LARGE_COEFF



### 整数計画問題の求解

# 孤立ループが無くなるまで試行を繰り返す
count = 0
while True:
	# 整数計画問題の出力
	#print(problem, file=sys.stderr)

	# 求解
	status = problem.solve(solver)

	# 最長路が見つからなかった場合は終了
	if status != 1:
		optimal = -float('inf')
		break

	# 試行結果のダンプ
	count += 1
	optimal = round(pulp.value(problem.objective))
	print('', file=sys.stderr)
	print('----- 試行 {0} 回目 -----'.format(count), file=sys.stderr)
	print('判定: {0}'.format(pulp.LpStatus[status]), file=sys.stderr)
	print('総延長: {0}'.format(optimal), file=sys.stderr)

	# 経路に含まれる枝
	xs = [ id for id in range(len(edges)) if x[id].value() >= 0.99 ]
	ys = [ id for id in range(len(edges)) if y[id].value() >= 0.99 ]
	zs = [ id for id in range(len(edges)) if z[id].value() >= 0.99 ]

	# 主経路の始点
	print('[major path]', file=sys.stderr)
	major_path = []
	if ys:
		id = ys[0]
		ys.remove(id)
		edges[id].direction = Direction.DIRECTION_1_TO_2
		print(edges[id].tsv, file=sys.stderr)
		major_path.append(edges[id])
		station = edges[id].station2
	elif zs:
		id = zs[0]
		zs.remove(id)
		edges[id].direction = Direction.DIRECTION_2_TO_1
		print(edges[id].tsv, file=sys.stderr)
		major_path.append(edges[id])
		station = edges[id].station1
	else:
		raise ValueError('主経路の始点が見つかりません')

	# 主経路の走査
	while True:
		candidates = [ id for id in xs if edges[id].station1 == station ]
		if candidates:
			id = candidates[0]
			xs.remove(id)
			edges[id].direction = Direction.DIRECTION_1_TO_2
			print(edges[id].tsv, file=sys.stderr)
			major_path.append(edges[id])
			station = edges[id].station2
			continue

		candidates = [ id for id in xs if edges[id].station2 == station ]
		if candidates:
			id = candidates[0]
			xs.remove(id)
			edges[id].direction = Direction.DIRECTION_2_TO_1
			print(edges[id].tsv, file=sys.stderr)
			major_path.append(edges[id])
			station = edges[id].station1
			continue

		candidates = [ id for id in zs if edges[id].station1 == station ]
		if candidates:
			id = candidates[0]
			zs.remove(id)
			edges[id].direction = Direction.DIRECTION_1_TO_2
			print(edges[id].tsv, file=sys.stderr)
			major_path.append(edges[id])
			station = edges[id].station2
			break

		candidates = [ id for id in ys if edges[id].station2 == station ]
		if candidates:
			id = candidates[0]
			ys.remove(id)
			edges[id].direction = Direction.DIRECTION_2_TO_1
			print(edges[id].tsv, file=sys.stderr)
			major_path.append(edges[id])
			station = edges[id].station1
			break

		raise ValueError(station + '駅で経路が途切れました')

	# 孤立ループが存在しなければ終了
	if not xs:
		break

	# 孤立ループの走査と条件式の追加
	station = None
	while xs:
		if not station:
			print('[minor loop]', file=sys.stderr)
			expr = 0
			station = edges[xs[0]].station1

		candidates = [ id for id in xs if edges[id].station1 == station ]
		if candidates:
			id = candidates[0]
			xs.remove(id)
			edges[id].direction = Direction.DIRECTION_1_TO_2
			print(edges[id].tsv, file=sys.stderr)
			station = edges[id].station2
			expr += 1 - x[id]
			continue

		candidates = [ id for id in xs if edges[id].station2 == station ]
		if candidates:
			id = candidates[0]
			xs.remove(id)
			edges[id].direction = Direction.DIRECTION_2_TO_1
			print(edges[id].tsv, file=sys.stderr)
			station = edges[id].station1
			expr += 1 - x[id]
			continue

		problem += expr >= 1
		station = None

	problem += expr >= 1



### 最長路が唯1本の枝のみからなるケース

for edge in edges:
	if edge.distance > optimal:
		major_path = [edge]
		optimal = edge.distance

if not major_path:
	print('最長路が見つかりませんでした', file=sys.stderr)
	sys.exit(1)



### 結果の正規化と出力 (任意性のある部分は駅名の辞書順で最も若いものを出力する)

loop1 = [ id for id in range(len(major_path)) if major_path[id].station_s == major_path[ 0].station_s and id > 0 ]
loop2 = [ id for id in range(len(major_path)) if major_path[id].station_s == major_path[-1].station_e ]

# Type L
if not loop1 and not loop2:
	if major_path[0].station_s > major_path[-1].station_e:
		major_path = reverse_path(major_path)
	print_path(major_path)

# Type O
elif loop2 == [0]:
	stations = list(map(lambda edge: edge.station_s, major_path))
	id = stations.index(min(stations))
	major_path = major_path[id:] + major_path[:id]
	if major_path[0].station_e > major_path[-1].station_s:
		major_path = reverse_path(major_path)
	print_path(major_path)

# Type P (順方向)
elif not loop1:
	id = loop2[0]
	path1 = major_path[:id]	# 放射部
	path2 = major_path[id:]	# 環状部
	if path2[0].station_e > path2[-1].station_s:
		path2 = reverse_path(path2)
	print_path(path1 + path2)

# Type P (逆方向)
elif not loop2:
	id = loop1[0]
	path1 = major_path[id:]	# 放射部
	path2 = major_path[:id]	# 環状部
	if path2[0].station_e > path2[-1].station_s:
		path2 = reverse_path(path2)
	print_path(reverse_path(path1) + path2)

# Type B (８)
elif len(loop2) > 1:
	id = loop1[0]
	path1 = major_path[:id]	# 環状部1
	path2 = major_path[id:]	# 環状部2
	if path1[0].station_e > path1[-1].station_s:
		path1 = reverse_path(path1)
	if path2[0].station_e > path2[-1].station_s:
		path2 = reverse_path(path2)
	if path1[0].station_e < path2[0].station_e:
		print_path(path1 + path2)
	else:
		print_path(path2 + path1)

# Type B (呂)
elif loop1[0] < loop2[0]:
	id1 = loop1[0]
	id2 = loop2[0]
	path1 = major_path[:id1]	# 環状部1
	path2 = major_path[id1:id2]	# 接続部
	path3 = major_path[id2:]	# 環状部2
	if path1[0].station_e > path1[-1].station_s:
		path1 = reverse_path(path1)
	if path3[0].station_e > path3[-1].station_s:
		path3 = reverse_path(path3)
	if path1[0].station_s < path3[0].station_s:
		print_path(path1 + path2 + path3)
	else:
		print_path(path3 + reverse_path(path2) + path1)

# Type B (日)
else:
	id1 = loop1[0]
	id2 = loop2[0]
	path1 = major_path[:id2]
	path2 = reverse_path(major_path[id2:id1])
	path3 = major_path[id1:]
	if path1[0].station_s > path1[-1].station_e:
		path1 = reverse_path(path1)
		path2 = reverse_path(path2)
		path3 = reverse_path(path3)
	if path1[0].station_e > path2[0].station_e:
		path1, path2 = path2, path1
	if path1[0].station_e > path3[0].station_e:
		path1, path3 = path3, path1
	if path2[-1].station_s > path3[-1].station_s:
		path2, path3 = path3, path2
	print_path(path1 + reverse_path(path2) + path3)


