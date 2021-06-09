# byznl

### Config.json 解释
{
    "weibo_home_page":[],
    "znl_num": [],
    "start_time": [],
    "file": [],
    "group_num": 4,
    "fast": false
}
##### weibo_home_page: List[str], weibo主页网址
##### znl_num: List[Integer], znl微博数目
##### start_time: List[str], znl微博开始时间，请保持%Y:%M:%D %h:%m格式，如2021-06-08 11:00
##### file: List[str], 当前目录下的文件名，文件内容为每行一条微博链接
##### group_num: Integer, 分享到几个群里
##### fast: Boolean(true/false), true为快速甩链接，false为慢速
> 请将znl_num或者start_time置为empty list，仅支持根据znl_num**或**start_time爬取链接


### Following Work 
[ ] end page bug fix
