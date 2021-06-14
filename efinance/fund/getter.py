import os
import re
from typing import List, Union
import pandas as pd
import requests
from tqdm import tqdm
import multitasking
import signal
from .config import EastmoneyFundHeaders
signal.signal(signal.SIGINT, multitasking.killall)


def get_quote_history(fund_code: str, pz: int = 40000) -> pd.DataFrame:
    """
    根据基金代码和要获取的页码抓取基金净值信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    pz : int, optional
        页码, 默认为 40000 以获取全部历史数据

    Returns
    -------
    DataFrame
        包含基金历史净值等数据
    """

    data = {
        'FCODE': f'{fund_code}',
        'IsShareNet': 'true',
        'MobileKey': '1',
        'appType': 'ttjj',
        'appVersion': '6.2.8',
        'cToken': '1',
        'deviceid': '1',
        'pageIndex': '1',
        'pageSize': f'{pz}',
        'plat': 'Iphone',
        'product': 'EFund',
        'serverVersion': '6.2.8',
        'uToken': '1',
        'userId': '1',
        'version': '6.2.8'
    }
    url = 'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNHisNetList'
    json_response = requests.get(
        url, headers=EastmoneyFundHeaders, data=data).json()
    rows = []
    columns = ['日期', '单位净值', '累计净值', '涨跌幅']
    if json_response is None:
        return pd.DataFrame(rows, columns=columns)
    datas = json_response['Datas']
    if len(datas) == 0:
        return pd.DataFrame(rows, columns=columns)
    rows = []
    for stock in datas:
        date = stock['FSRQ']
        rows.append({
            '日期': date,
            '单位净值': stock['DWJZ'],
            '累计净值': stock['LJJZ'],
            '涨跌幅': stock['JZZZL']
        })

    df = pd.DataFrame(rows)
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')

    df['累计净值'] = pd.to_numeric(df['累计净值'], errors='coerce')

    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    return df


def get_realtime_increase_rate(fund_codes: Union[List[str], str]) -> pd.DataFrame:
    """
    获取基金实时估算涨跌幅度

    Parameters
    ----------
    fund_codes : Union[List[str], str]
        6 位基金代码或者 6 位基金代码构成的字符串列表

    Returns
    -------
    DataFrame
        单只或者多只基金实时估算涨跌情况
    """

    if not isinstance(fund_codes, list):
        fund_codes = [fund_codes]
    data = {
        'pageIndex': '1',
        'pageSize': '300000',
        'Sort': '',
        'Fcodes': ",".join(fund_codes),
        'SortColumn': '',
        'IsShowSE': 'false',
        'P': 'F',
        'deviceid': '3EA024C2-7F22-408B-95E4-383D38160FB3',
        'plat': 'Iphone',
        'product': 'EFund',
        'version': '6.2.8',
    }

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo', headers=EastmoneyFundHeaders, data=data).json()
    data_list = json_response['Datas']

    columns = ['基金代码', '名称', '估算涨跌幅', '估算时间']
    rows = []
    for fund in data_list:
        code = fund['FCODE']
        name = fund['SHORTNAME']
        rate = fund['GSZZL']
        gztime = fund['GZTIME']
        rows.append([code, name, rate, gztime])
    df = pd.DataFrame(rows, columns=columns)
    return df


def get_fund_codes(ft: str = None) -> pd.DataFrame:
    """
    获取天天基金网公开的全部公墓基金名单

    Parameters
    ----------
    ft : str, optional
        基金类型
            'zq' : 债券类型基金
            'gp' : 股票类型基金
            None : 全部

    Returns
    -------
    DataFrame
        包含天天基金网基金名单数据
    """

    params = [
        ('op', 'ph'),
        ('dt', 'kf'),
        ('rs', ''),
        ('gs', '0'),
        ('sc', '6yzf'),
        ('st', 'desc'),
        ('qdii', ''),
        ('tabSubtype', ',,,,,'),
        ('pi', '1'),
        ('pn', '50000'),
        ('dx', '1'),
        ('v', '0.09350685300919159'),
    ]
    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
        'Accept': '*/*',
        'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }
    if ft is not None and ft in ['gp', 'zq']:
        params.append(('ft', ft))

    response = requests.get(
        'http://fund.eastmoney.com/data/rankhandler.aspx', headers=headers, params=params)
    results = re.findall('(\d{6}),(.*?),', response.text)
    columns = ['基金代码', '基金简称']
    results = re.findall('(\d{6}),(.*?),', response.text)
    df = pd.DataFrame(results, columns=columns)
    return df


def get_inverst_postion(fund_code: str, dates: Union[str, List[str]] = None) -> pd.DataFrame:
    """
    获取基金持仓占比信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[str, List[str]], optional
        日期或日期组成的列表
        例如：
            None : 表示最新公开持仓数据的日期
            '2020-09-30' 表示指定日期数据

    Returns
    -------
    DataFrame
        包含指定基金特定日期的公开持仓信息
    """

    columns = {
        'GPDM': '股票代码',
        'GPJC': '股票简称',
        'JZBL': '持仓占比',
        'PCTNVCHG': '较上期变化',
    }
    df = pd.DataFrame(columns=columns.values())
    if not isinstance(dates, List):
        dates = [dates]

    for date in dates:
        params = [
            ('FCODE', fund_code),
            ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('OSVersion', '14.3'),
            ('appType', 'ttjj'),
            ('appVersion', '6.2.8'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('passportid', '3061335960830820'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.2.8'),
            ('uToken', '6cfr1qdanf8nfhd6uc6u-hdj86f1f8kfe9f8k108.6'),
            ('userId', 'f8d95b2330d84d9e804e7f28a802d809'),
            ('version', '6.2.8'),
        ]
        if date is not None:
            params.append(('DATE', date))
        params = tuple(params)
        response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition',
                                headers=EastmoneyFundHeaders, params=params)
        stocks = response.json()['Datas']['fundStocks']

        if stocks is None or len(stocks) == 0:
            continue

        _df = pd.DataFrame(stocks)
        _df = _df[list(columns.keys())].rename(columns=columns)
        _df['公开日期'] = [date for _ in range(len(_df))]
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


def get_period_change(fund_code: str) -> pd.DataFrame:
    """
    获取基金阶段涨跌幅度

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    DataFrame
        包含指定基金的阶段涨跌数据
    """

    params = (
        ('AppVersion', '6.3.8'),
        ('FCODE', fund_code),
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('passportid', '3061335960830820'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('version', '6.3.6'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNPeriodIncrease', headers=EastmoneyFundHeaders, params=params).json()
    columns = {

        'syl': '收益率',
        'avg': '同类平均',
        'rank': '同类排行',
        'sc': '同类总数',
        'title': '时间段'

    }
    titles = {'Z': '近一周',
              'Y': '近一月',
              '3Y': '近三月',
              '6Y': '近六月',
              '1N': '近一年',
              '2Y': '近两年',
              '3N': '近三年',
              '5N': '近五年',
              'JN': '今年以来',
              'LN': '成立以来'}
    # 发行时间
    ESTABDATE = json_response['Expansion']['ESTABDATE']
    df = pd.DataFrame(json_response['Datas'])

    df = df[list(columns.keys())].rename(columns=columns)
    df['时间段'] = titles.values()
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


def get_public_dates(fund_code: str) -> List[str]:
    """
    获取历史上更新持仓情况的日期列表

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    List[str]
        指定基金公开持仓的日期列表
    """

    params = (
        ('FCODE', fund_code),
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('cToken', 'a6hdhrfejje88ruaeduau1rdufna1e--.6'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('passportid', '3061335960830820'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('serverVersion', '6.3.6'),
        ('uToken', 'a166hhqnrajucnfcjkfkeducanekj1dd1cc2a-e9.6'),
        ('userId', 'f8d95b2330d84d9e804e7f28a802d809'),
        ('version', '6.3.8'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNIVInfoMultiple', headers=EastmoneyFundHeaders, params=params).json()
    if json_response['Datas'] is None:
        return []
    return json_response['Datas']


def get_types_persentage(fund_code: str, dates: Union[List[str], str, None] = None) -> pd.DataFrame:
    """
    获取指定基金不同类型占比信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[List[str], str, None]
        可选值类型示例如下
            None : 最新公开持仓数据的日期

            '2020-09-30' 指定日期数据

    Returns
    -------
    DataFrame
        指定基金的在不同日期的不同类型持仓占比信息
    """

    columns = {
        'GP': '股票比重',
        'ZQ': '债券比重',
        'HB': '现金比重',
        'JZC': '总规模(亿元)',
        'QT': '其他比重'
    }
    df = pd.DataFrame(columns=columns.values())
    if not isinstance(dates, List):
        dates = [dates]
    for date in dates:
        params = [
            ('FCODE', fund_code),
            ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('OSVersion', '14.3'),
            ('appVersion', '6.3.8'),
            ('cToken', 'a6hdhrfejje88ruaeduau1rdufna1e--.6'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('passportid', '3061335960830820'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.3.6'),
            ('uToken', 'a166hhqnrajucnfcjkfkeducanekj1dd1cc2a-e9.6'),
            ('userId', 'f8d95b2330d84d9e804e7f28a802d809'),
            ('version', '6.3.8'),
        ]
        if date is not None:
            params.append(('DATE', date))
        params = tuple(params)
        json_response = requests.get(
            'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNAssetAllocationNew',  params=params).json()

        if len(json_response['Datas']) == 0:
            continue
        _df = pd.DataFrame(json_response['Datas'])[columns.keys()]
        _df = _df.rename(columns=columns)
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


def get_base_info_single(fund_code: str) -> pd.Series:
    """
    获取基金的一些基本信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    Series
        包含基金的一些基本信息
    """

    params = (
        ('FCODE', fund_code),
        ('utoken', 'a166hhqnrajucnfcjkfkeducanekj1dd1cc2a-e9.6'),
        ('userid', 'f8d95b2330d84d9e804e7f28a802d809'),
        ('passportutoken', 'FobyicMgeV4hdZSOHFSgW9W8PVUCQvTszyG6Mi16M0wZoNP96cXx1I25vT8UuLzqdUKtL93LFEHUMqjK4fmOO3DfE3Uogsm8IVjbgp1UNXnzfSM6mQwLCZO6PDQpA9Ak3c9Ow81EfCAT4qgkLz7tgls17FJPTeWx8tHo0pSrXj1ijjoVxUh1MTqvGnmXjIOS6FPNY72T7n388PNiH4HWw_fwR_n2MPgoSjLzPqayO0WPY79cEaXCVkxdNYHpRAJyUVDBhDvQ6BGGyd1Ftl-eWiYb18kvVDr6q4AFHOlj-Uyx-IfMpYpZkir7F02jyqpB'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('ctoken', 'a6hdhrfejje88ruaeduau1rdufna1e--.6'),
        ('plat', 'Iphone'),
        ('passportctoken', 'F5khCNKSAVOwvKQt3M-8HrFIpXuyk1NcGXSRQHyWQkneJuQJT25-QDvb4GiMk5O03mAPhMcU4SE9aWKEWW5mkRwTfg38mCkfSspZH2eXQnrewIBtqV-VhsMHKXT_1ILhqgPcCaNxkxF9t51IXVOlVn4kj2r3ogDcLoL2bo-2fJg'),
        ('product', 'EFund'),
        ('version', '6.3.8'),
        ('GTOKEN', '98B423068C1F4DEF9842F82ADF08C5db'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNNBasicInformation', headers=EastmoneyFundHeaders, params=params).json()
    columns = {
        'FCODE': '基金代码',
        'SHORTNAME': '基金简称',
        'ESTABDATE': '成立日期',
        'RZDF': '涨跌幅',
        'DWJZ': '最新净值',
        'JJGS': '基金公司',
        'FSRQ': '净值更新日期',
        'COMMENTS': '简介',
    }
    s = pd.Series(json_response['Datas']).rename(index=columns)
    s = s.apply(lambda x: x.replace('\n', ' ').strip()
                if isinstance(x, str) else x)
    return s


def get_base_info_muliti(fund_codes: List[str]) -> pd.Series:
    """
    获取多只基金基本信息

    Parameters
    ----------
    fund_codes : List[str]
        6 位基金代码列表

    Returns
    -------
    Series
        包含多只基金基本信息
    """

    ss = []

    @multitasking.task
    def start(fund_code: str) -> None:
        s = get_base_info_single(fund_code)
        ss.append(s)
        bar.update()
        bar.set_description(f'processing {fund_code}')
    bar = tqdm(total=len(fund_codes))
    for fund_code in fund_codes:
        start(fund_code)
    multitasking.wait_for_tasks()
    df = pd.DataFrame(ss)
    return df


def get_base_info(fund_codes: Union[str, List[str]]) -> Union[pd.Series, pd.DataFrame]:
    """
    获取基金的一些基本信息

    Parameters
    ----------
    fund_codes : Union[str, List[str]]
        6 位基金代码 或多个 6 位 基金代码构成的列表

    Returns
    -------
    Union[pd.Series, pd.DataFrame]
        Series : 包含单只基金基本信息(当 fund_codes 是字符串时)
        DataFrane : 包含多只股票基本信息(当 fund_codes 是字符串列表时)

    Raises
    ------
    TypeError
        当 fund_codes 类型不符合要求时
    """

    if isinstance(fund_codes, str):
        return get_base_info_single(fund_codes)
    elif hasattr(fund_codes, '__iter__'):
        return get_base_info_muliti(fund_codes)
    raise TypeError(f'所给的 {fund_codes} 不符合参数要求')


def get_industry_distributing(fund_code: str, dates: Union[str, List[str]] = None) -> pd.DataFrame:
    """
    获取指定基金行业分布信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[str, List[str]], optional
        日期
        可选值类型示例如下
            None : 最新公开日期
            '2020-01-01' : 一个公开持仓日期
            ['2020-12-31' ,'2019-12-31'] : 多个公开持仓日期

    Returns
    -------
    DataFrame
        包含指定基金行业持仓信息
    """

    columns = {
        'HYMC': '行业名称',
        'ZJZBL': '持仓比例',
        'FSRQ': '公布日期',
        'SZ': '市值'
    }
    df = pd.DataFrame(columns=columns.values())
    if isinstance(dates, str):
        dates = [dates]
    for date in dates:

        params = [

            ('FCODE', fund_code),
            ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('OSVersion', '14.4'),
            ('appVersion', '6.3.8'),
            ('cToken', '1fnc-1nne8cjcrdqud6rhrqqjee8fn-j.6'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('passportid', '3061335960830820'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.3.6'),
            ('uToken', 'nnukrkhk-aake6k1ehj-d-c86fua-ck-1fx6j882.6'),
            ('userId', 'f8d95b2330d84d9e804e7f28a802d809'),
            ('version', '6.3.8'),
        ]
        if date is not None:
            params.append(('DATE', date))

        response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNSectorAllocation',
                                headers=EastmoneyFundHeaders, params=params)
        datas = response.json()['Datas']
        _df = pd.DataFrame(datas)
        _df = _df.rename(columns=columns)
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    df = df.drop_duplicates()
    return df


def get_pdf_reports(fund_code: str, max_count: int = 12, save_dir: str = 'pdf') -> None:
    """
    根据基金代码获取其全部 pdf 报告

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    max_count : int, optional
        要获取的最大个数个 pdf(从最新的的开始数), 默认为 12
    save_dir : str, optional
        pdf 保存的文件夹路径, 默认为 'pdf'
    """

    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36 Edg/89.0.774.77',
        'Accept': '*/*',
        'Referer': 'http://fundf10.eastmoney.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }

    @multitasking.task
    def download_file(fund_code: str, url: str, filename: str, file_type='.pdf') -> None:
        """
        根据文件名、文件直链等参数下载文件

        Parameters
        ----------
        fund_code : str
            6 位基金代码
        url : str
            下载连接
        filename : str
            文件后缀名
        file_type : str, optional
            文件类型, 默认为 '.pdf'
        """

        bar.set_description(f'processing {fund_code}')
        fund_code = str(fund_code)
        if not os.path.exists(save_dir+'/'+fund_code):
            os.mkdir(save_dir+'/'+fund_code)
        response = requests.get(url, headers=headers)
        path = f'{save_dir}/{fund_code}/{filename}{file_type}'
        with open(path, 'wb') as f:
            f.write(response.content)
        if os.path.getsize(path) == 0:
            os.remove(path)
            return
        bar.update(1)
    params = (
        ('fundcode', fund_code),
        ('pageIndex', '1'),
        ('pageSize', '200000'),
        ('type', '3'),
    )

    json_response = requests.get(
        'http://api.fund.eastmoney.com/f10/JJGG', headers=headers, params=params).json()

    base_link = 'http://pdf.dfcfw.com/pdf/H2_{}_1.pdf'

    bar = tqdm(total=min(max_count, len(json_response['Data'])))
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    for item in json_response['Data'][-max_count:]:

        title = item['TITLE']
        download_url = base_link.format(item['ID'])
        download_file(fund_code, download_url, title)
    multitasking.wait_for_tasks()
    bar.close()
