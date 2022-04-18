import os					# osの情報
import sys					# Pythonバージョン
import time					# sleepなどの時間系
import datetime				# 日付
import enum					# 列挙子
import base64				# base64の変換を行う
import json					# JSONファイルを扱う
import re					# 正規表現
import threading			# マルチスレッド
import subprocess			# 外部プログラム実行用
import platform				# OS情報
import urllib.request		# urlを扱うモジュール
import urllib.error			# urllibのエラー定義
import inspect				# 活動中のオブジェクトの情報を取得する ( エラー位置 )
import traceback			# スタックトレースの取得
import chardet				# 文字コードを判断する

__version__ = "1.11.0"
OUTPUT_DIR = "./data"								# 情報を出力する際のディレクトリ
LOG_PATH = OUTPUT_DIR + "/lib.log"					# ログのファイルパス
ERROR_LOG_PATH = OUTPUT_DIR + "/error.log"			# エラーログのファイルパス
DISPLAY_DEBUG_LOG_FLAG = True						# デバッグログを出力するかどうか

# ライブラリ内エラーコード
class LibErrorCode(enum.Enum):
	success = enum.auto()			# 成功
	file = enum.auto()				# ファイルのエラー
	http = enum.auto()				# http通信のエラー
	argument = enum.auto()			# 引数が原因のエラー
	cancel = enum.auto()			# 前提条件不一致で処理がキャンセルされたときのエラー
	unknown = enum.auto()			# 不明なエラー
	
# ２次元ベクトルの値を保存する構造体
class Vector2():
	def __init__(self, x = None, y = None):
		if x is None:			# 値を指定されなければ 0 で初期化する
			self.x = 0
			self.y = 0
			return

		self.x = x
		if y is not None:
			self.y = y
		else:
			self.y = x			# x のみ指定されていれば両方同じ値で指定する
		return

	def __str__(self):
		return "x={}, y={}".format(self.x, self.y)
	def __repr__(self):
		return self.__str__()

# Jsonデータを読み込んで保持するクラス
class JsonData():
	# コンストラクタ
	def __init__(self, keys, default, path):
		self.keys = keys
		self.default = default
		self.path = path
		self.data = None
		self.load_error_flag = False
		self.load()
		return

	# ファイルからデータを取得する
	def load(self):
		try:
			with open(self.path, encoding="utf-8") as f:
				json_data = json.load(f)								# JSONファイルを読み込む
				if type(self.keys) is not list and type(self.keys) is not tuple:
					self.keys = (self.keys,)							# タプルでもリストでもなければタプルに加工する
				try:
					for row in self.keys:
						json_data = json_data[row]						# キーの名前をたどっていく
					self.data = json_data
					return True
				except KeyError as e:
					self.data = self.default							# キーが見つからなければデフォルト値を設定する
					print_debug(e)
					return True
		except FileNotFoundError as e:									# ファイルが見つからなかった場合はデフォルト値を設定する
			self.data = self.default
			return True
		except Exception as e:
			self.data = self.default
			self.load_error_flag = True
			print_error_log("jsonファイルの読み込みに失敗しました [keys={}]\n{}".format(self.keys, e))
		return False

	# ファイルにデータを書き込む
	def save(self):
		if self.load_error_flag:
			print_error_log("データの読み込みに失敗しているため、上書き保存をスキップしました")
			return False
		json_data = {}
		try:
			with open(self.path, encoding="utf-8") as f:
				json_data = json.load(f)					# JSONファイルを読み込む
		except FileNotFoundError as e:						# ファイルが見つからなかった場合は
			print_log("jsonファイルが見つからなかったため、新規生成します [keys={}]\n{}".format(self.keys, e))
		except json.decoder.JSONDecodeError as e:			# JSONの文法エラーがあった場合は新たに上書き保存する
			print_log("jsonファイルが壊れている為、再生成します [keys={}]\n{}".format(self.keys, e))
		except Exception as e:								# 不明なエラーが起きた場合は上書きせず終了する
			print_error_log("jsonファイルへのデータの保存に失敗しました [keys={}]\n{}".format(self.keys, e))
			return False
		try:
			update_nest_dict(json_data, self.keys, self.data)
			json_str = json.dumps(json_data, indent=4, ensure_ascii=False)		# 文字列として出力する
			with open(self.path, "w", encoding="utf-8") as f:
				f.write(json_str)												# ファイルに出力する
				return True
		except Exception as e:
			print_error_log("jsonへの出力に失敗しました [keys={}]\n{}".format(self.keys, e))
		return False

	# 値をインクリメントしてファイルに保存する ( 数値以外が保存されていた場合は 0 で初期化 )
	def increment(self, save_flag = False, num = 1):
		if not can_cast(self.get(), int):							# int型に変換できない場合は初期化する
			self.set(0)
		return self.set(int(self.get()) + num, save_flag)			# 一つインクリメントして値を保存する

	# 保存されている値を取得する
	def get(self):
		return self.data

	# 新しい値を登録する
	def set(self, data, save_flag = False):
		self.data = data
		if save_flag:
			return self.save()				# 保存フラグが立っていれば保存する
		return False						# 保存無し

	# キー名を取得する
	def get_keys(self):
		return self.keys

	# デフォルト値を取得する
	def get_default(self):
		return self.default

	# JSON文字列を整形して print 出力する
	@staticmethod
	def dumps(json_data):
		if type(json_data) is str:
			data = json.loads(json_data)
		elif type(json_data) is dict:
			data = json_data
		else:
			print_debug("JSONデータの読み込みに失敗しました")
			return None

		data_str = json.dumps(data, indent=4, ensure_ascii=False)
		print(data_str)
		return data_str


# 関数をマルチスレッドで実行するためのデコレーター
def thread(func):
	def inner(*args, **kwargs):
		th = threading.Thread(target=lambda: func(*args, **kwargs))
		th.start()
		return
	return inner


# ライブラリ内で使用するディレクトリを作成する
def make_lib_dir():
	os.makedirs(OUTPUT_DIR, exist_ok=True)		# データを出力するディレクトリを生成する
	return

# ライブラリ内エラーコードからエラーメッセージを取得する
def get_error_message(code):
	if code == LibErrorCode.success:
		return "処理が正常に終了しました"
	elif code == LibErrorCode.file:
		return "ファイル関係のエラーが発生しました"
	elif code == LibErrorCode.http:
		return "HTTP通信関係のエラーが発生しました"
	elif code == LibErrorCode.argument:
		return "引数が適切ではありません"
	elif code == LibErrorCode.cancel:
		return "処理がキャンセルされました"
	elif code == LibErrorCode.unknown:
		return "不明なエラーが発生しました"
	else:
		print_error_log("登録されていないエラーコードが呼ばれました", console_print=False)
		return "エラーが発生しました"
	return ""

# ログを出力する
def print_log(message, console_print = True, error_flag = False):
	log_path = LOG_PATH
	if error_flag:					# エラーログの場合はファイルを変更する
		log_path = ERROR_LOG_PATH
	if console_print:
		print(message)
	
	time_now = get_datatime_now(True)					# 現在時刻を取得する
	if not os.path.isfile(log_path) or os.path.getsize(log_path) < 1024*1000*50:		# 50MBより小さければ出力する
		os.makedirs(OUTPUT_DIR, exist_ok=True)											# データを出力するディレクトリを生成する
		with open(log_path, mode="a", encoding="utf-8") as f:
			if error_flag:		# エラーログ
				frame = inspect.currentframe().f_back.f_back				# 関数が呼ばれた場所の情報を取得する
				try:
					class_name = str(frame.f_locals["self"])
					class_name = re.match(r'.*?__main__.(.*?) .*?', class_name)
					if class_name is not None:
						class_name = class_name.group(1)
				except KeyError:											# クラス名が見つからなければ
					class_name = None
				file_name = os.path.splitext(os.path.basename(frame.f_code.co_filename))[0]

				code_name = ""
				if class_name is not None:
					code_name = "{}.{}.{}({})".format(file_name, class_name, frame.f_code.co_name, frame.f_lineno)
				else:
					code_name = "{}.{}({})".format(file_name, frame.f_code.co_name, frame.f_lineno)
				f.write("[{}] {}".format(time_now, code_name).ljust(90)
				+ str(message).rstrip("\n").replace("\n", "\n" + "[{}]".format(time_now).ljust(90)) + "\n")		# 最後の改行文字を取り除いて文中の改行前にスペースを追加する
			else:						# 普通のログ
				f.write("[{}] {}\n".format(time_now, str(message).rstrip("\n")))
			return True
	else:
		print("ログファイルの容量がいっぱいの為、出力を中止しました")
	return False

# エラーログを出力する
def print_error_log(message, console_print = True):
	return print_log(message, console_print, True)

# デバッグログを出力する
def print_debug(message, end = "\n"):
	if DISPLAY_DEBUG_LOG_FLAG:
		print(message, end=end)
	return DISPLAY_DEBUG_LOG_FLAG

# ネストされた辞書内の特定の値のみを再帰で変更する関数
def update_nest_dict(dictionary, keys, value):
	if type(keys) is not list and type(keys) is not tuple:
		keys = (keys,)													# 渡されがキーがリストでもタプルでもなければタプルに変換する
	if len(keys) == 1:
		dictionary[keys[0]] = value										# 最深部に到達したら値を更新する
		return True
	if keys[0] in dictionary:
		update_nest_dict(dictionary[keys[0]], keys[1:], value)			# すでにキーがあればその内部から更に探す
	else:
		dictionary[keys[0]] = {}										# キーが存在しなければ空の辞書を追加する
		update_nest_dict(dictionary[keys[0]], keys[1:], value)
	return False

# リンク先が存在するかどうかを確認する
def check_url(url):
	try:
		f = urllib.request.urlopen(url)
		f.close()
		time.sleep(0.1)
	except Exception:
		return False		# 失敗
	return True				# 成功

# インターネット上からファイルをダウンロードする関数 ( LibErrorCodeを返す )
def download_file(url, dst_path, overwrite = True):
	if not overwrite and os.path.isfile(dst_path):
		return LibErrorCode.cancel

	try:
		with urllib.request.urlopen(url) as web_file:
			data = web_file.read()
			with open(dst_path, mode="wb") as local_file:
				local_file.write(data)
				time.sleep(0.1)
				return LibErrorCode.success
			return LibErrorCode.file
	except urllib.error.HTTPError as e:
		print_error_log(e)
		print_error_log(url)
		return LibErrorCode.argument		# HTTPエラーが発生した場合は引数エラーを返す
	except urllib.error.URLError as e:
		print_error_log(e)
		print_error_log(url)
		return LibErrorCode.http
	return LibErrorCode.unknown

# ファイルをダウンロードして、失敗時に再ダウンロードを試みる関数
def download_and_check_file(url, dst_path, overwrite = True):
	TRIAL_NUM = 100						# 失敗時の試行回数
	TRIAL_INTERVAL = 5					# 再ダウンロード時のクールタイム
	result = download_file(url, dst_path, overwrite)
	if result == LibErrorCode.cancel:	# 既にファイルが存在した場合ののみ処理を終了する
		return True
	for i in range(TRIAL_NUM):
		if not os.path.isfile(dst_path):
			print_error_log("ダウンロードに失敗しました、" + str(TRIAL_INTERVAL) + "秒後に再ダウンロードします ( " + str(i + 1) + " Fail )")
			time.sleep(TRIAL_INTERVAL)
			result = download_file(url, dst_path, overwrite)	# 一度目はエラーコードに関わらず失敗すればもう一度ダウンロードする
			if result == LibErrorCode.argument:					# URLが間違っていれば処理を終了する
				return False
		else:						# ダウンロード成功
			return True
	return False

# ファイルを後ろから指定した行だけ読み込む
def read_tail(path, n, encoding = None):
	try:
		with open(path, "r", encoding=encoding) as f:
			lines = f.readlines()			# すべての行を取得する
	except FileNotFoundError:
		lines = []
	return lines[-n:]						# 後ろからn行だけ返す

# ファイルパスの指定した階層をリネームする
def rename_path(file_path, dest_name, up_hierarchy_num = 0, slash_only = False):
	file_name = ""
	for i in range(up_hierarchy_num):				# 指定された階層分だけパスの右側を避難する
		if i == 0:
			file_name = os.path.basename(file_path)
		else:
			file_name = os.path.join(os.path.basename(file_path), file_name)
		file_path = os.path.dirname(file_path)

	file_path = os.path.dirname(file_path)			# 一番深い階層を削除する
	file_path = os.path.join(file_path, dest_name)					# 一番深い階層を新しい名前で追加する
	if file_name != "":
		file_path = os.path.join(file_path, file_name)				# 避難したファイルパスを追加する
	if slash_only:
		file_path = file_path.replace("\\", "/")					# 引数で指定されていれば区切り文字をスラッシュで統一する
	return file_path

# 指定されたファイルが指定された文字コードでなければ指定された文字コードに変換する
def convert_file_encoding(path, encoding):
	if not os.path.isfile(path):
		return False
	with open(path, "rb") as f:
		file_charcode = chardet.detect(f.read())["encoding"]
	if file_charcode is None:
		return False
	if file_charcode == "Windows-1254":						# 誤判断される事が多いため、シフトJISということにする
		file_charcode = "shift_jis"

	if file_charcode.lower() != encoding.lower():			# 指定された文字コードでなければ
		with open(path, "r", encoding=file_charcode) as f:
			data = f.read()
		with open(path, "w", encoding=encoding) as f:
			f.write(data)
	return True

# プログラム終了時に一時停止する関数
def program_pause(program_end = True):
	if not False:	#__debug__:			# デバッグでなければ一時停止する
		if program_end:
			message = "Press Enter key to exit . . ."
		else:
			message = "Press Enter key to continue . . ."
		input(message)
	return

# 条件に一致する文字が入力されるまで再入力を求める入力関数 ( デフォルトでは空白のみキャンセル )
def imput_while(str_info, branch = lambda in_str : in_str != ""):
	while True:
		in_str = input(str_info)
		if branch(in_str):
			return in_str
		else:
			print("\n不正な値が入力されました、再度入力して下さい")
	return ""

# 日本の現在の datetime を取得する
def get_datatime_now(to_str = False):
	datetime_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9), "JST"))		# 日本の現在時刻を取得する
	if not to_str:
		return datetime_now
	return datetime_now.strftime("%Y-%m-%d %H:%M:%S")												# 文字列に変換する

# 16進数の文字列を圧縮、展開する
def compress_hex(hex_str, decompression = False):
	if decompression:														# 展開が指定されていれば展開する
		if type(hex_str) is not str:
			return ""														# 文字列以外が渡されたら空白の文字列を返す
		hex_str = hex_str.replace("-", "+").replace("_", "/")				# 安全な文字列をbase64の記号に復元する
		hex_str += "=" * (len(hex_str) % 4)									# 取り除いたパディングを復元する
		hex_str = hex_str.encode()

		hex_str = base64.b64decode(hex_str)
		hex_str = base64.b16encode(hex_str)
		return hex_str.decode()

	if type(hex_str) is str:
		hex_str = hex_str.encode()			# バイナリデータでなければバイナリに変換する
	if len(hex_str) % 2 != 0:
		hex_str = b"0" + hex_str			# 奇数の場合は先頭に0を追加して偶数にする

	hex_str = base64.b16decode(hex_str, casefold=True)
	hex_str = base64.b64encode(hex_str)
	return hex_str.decode().replace("=", "").replace("+", "-").replace("/", "_")			# パディングを取り除いて安全な文字列に変換する

# OSのコマンドを実行する
def subprocess_command(command):
	if platform.system() == "Windows":									# Windowsの環境ではコマンドプロンプトを表示しないようにする
		si = subprocess.STARTUPINFO()
		si.dwFlags |= subprocess.STARTF_USESHOWWINDOW					# コマンドプロンプトを表示しない
		return subprocess.check_output(command, startupinfo=si)
	else:																# STARTUPINFO が存在しない OS があるため処理を分岐する
		return subprocess.check_output(command)

# スタックされているエラーを表示する
def print_exc():
	if DISPLAY_DEBUG_LOG_FLAG:
		traceback.print_exc()
		print("\n")
		print(sys.exc_info())
	return

# キャストできるかどうかを確認する
def can_cast(x, cast_type):
	try:
		cast_type(x)
	except ValueError:
		return False
	return True

# Pythonのバージョン情報を文字列で取得する
def get_python_version():
	version = "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
	return version


'''
----------------------------------------------------------------------------------------------------------
ver.1.11.0 (2021/10/03)
ファイルパスの指定した階層をリネームする関数を追加
OSのコマンドを実行する関数を追加
print_debug 関数に引数 end を追加

----------------------------------------------------------------------------------------------------------
ver.1.10.1 (2021/07/16)
JsonData()クラスで、同時に同じファイルを更新しようとすると、ファイルのデータが初期化される不具合を修正
返り値の値を調整、JsonData.incrementをリファクタリング

----------------------------------------------------------------------------------------------------------
ver.1.10.0 (2021/06/06)
JSON文字列を整形して print 出力する関数を JsonData クラスに追加
関数をマルチスレッドで実行するためのデコレーターを追加
print_log関数でクラス名が存在しないときにクラッシュすることがある不具合を修正
PyLintを使用して、プログラムをリファクタリング

----------------------------------------------------------------------------------------------------------
ver.1.9.0 (2021/04/24)
２次元ベクトルの値を保存する構造体を追加
read_tail 関数で encoding を指定できるように引数を追加
print_log 関数のエラーログを出力する際の引数を bool 値のフラグを指定するだけで出力できるように簡略化

----------------------------------------------------------------------------------------------------------
ver.1.8.0 (2021/04/09)
エラーログに出力されるソースコードの情報にファイル名とクラス名を追加
エラーログが複数行の場合は、２行目以降の左の空白に日時が出力されるように変更
ログファイルの最大容量を 10MB から 50MB まで増加

----------------------------------------------------------------------------------------------------------
ver.1.7.0 (2021/03/13)
スタックされているエラーを表示する関数を追加
指定されたファイルが指定された文字コードでなければ指定された文字コードに変換する関数を追加
ネストされた辞書内の特定の値のみを再帰で変更する関数を JsonData クラス内からライブラリの関数に移動
ログを出力する際に OS のデフォルト文字コードで出力していたのを utf-8 で出力するように変更
JsonData クラスに値をインクリメントしてファイルに保存する関数を追加
JsonData クラスで扱うファイルの文字コードを OS のデフォルト文字コードから utf-8 に変更 ( 過去verで保存したファイルの読み込み不可 )
JsonData クラスで読み込んだJsonファイルに文法エラーがあった場合に、データを新しく上書き保存できない不具合を修正

----------------------------------------------------------------------------------------------------------
ver.1.6.0 (2021/03/07)
Jsonデータを読み込んで保持するクラスで、自由な数のキーを指定できる用に変更
キャストできるかどうかを確認する関数を追加

----------------------------------------------------------------------------------------------------------
ver.1.5.0 (2021/02/15)
ファイルを後ろから指定した行だけ読み込む関数を追加
16進数の文字列を圧縮、展開する関数を追加

----------------------------------------------------------------------------------------------------------
ver.1.4.0 (2021/01/12)
Pythonのバージョン情報を文字列で取得する関数を追加
デバッグログを出力する関数を追加
ログに出力する日付の計算に get_datatime_now 関数を使うように変更

----------------------------------------------------------------------------------------------------------
ver.1.3.1 (2020/12/24)
get_datatime 関数の名前を get_datatime_now に変更、文字列に変換した際のフォーマットを変更

----------------------------------------------------------------------------------------------------------
ver.1.3.0 (2020/12/01)
日本の現在の datetime を取得する関数を追加
Jsonデータを読み込んで保持するクラスを追加
初期化関数をライブラリ内で使用するディレクトリを作成する関数に名前を変更

----------------------------------------------------------------------------------------------------------
ver.1.2.1 (2020/11/24)
ログを出力する際に、元のメッセージの最後に改行が含まれていた場合は改行を削除するように調整
エラーログを出力する関数を複数行のログに対応
起動時の初期化処理を行う関数を作成

----------------------------------------------------------------------------------------------------------
ver.1.2.0 (2020/10/29)
条件に一致する文字が入力されるまで再入力を求める入力関数を追加

----------------------------------------------------------------------------------------------------------
ver.1.1.1 (2020/10/20)
download_file関数とdownload_and_check_file関数でファイルが既に存在する場合に上書きするかどうかを指定できる引数を追加

----------------------------------------------------------------------------------------------------------
ver.1.1.0 (2020/10/17)
通常のログを出力する関数を追加
プログラム終了時に一時停止する関数を追加
リンク先が存在するかどうかを確認する関数を追加
ライブラリ内エラーコードからエラーメッセージを取得する関数を追加
列挙型のライブラリ内エラーコードを追加

インターネット上からファイルをダウンロードする関数で、存在しないURLを指定するとクラッシュする不具合を修正
print_log関数に文字列以外のものを渡した際にクラッシュする不具合を修正

----------------------------------------------------------------------------------------------------------
ver.1.0.0 (2020/10/15)
初版
エラーログを出力する関数を実装
インターネット上からファイルをダウンロードする関数を追加
ファイルをダウンロードして、失敗時に再ダウンロードを試みる関数
'''