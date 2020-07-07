# Interview for Data Scientist

## 项目篇:
### 遇到问题的改进思路和应对措施

### 1. 想知道用户有记录的比例怎么做，我这个数据提取主要分析什么，之后有什么用，还有什么什么数据怎么用

### 2. 不平衡样本的处理

### 3. 假设五月份第四周天猫女装类的GMV出现整体下滑，你觉得可以怎么分析？

### 4. 长期的人均活跃时长下降该怎么分析？抖音男性活跃时长比女性怎么分析？关于AB test和统计样本分配的一些问题

## 知识篇:
### 1. 概率论--贝叶斯公式,全概率公式
#### 1.1 贝叶斯公式
贝叶斯的数学公式十分简单

    一， 你要有<b>先验概率P（A）</b>  

    二， <b>似然性 P（B|A）</b>  

    三,  最终得到<b>后验概率P（A|B）</b>。这三者构成贝叶斯统计的三要素。  

似然性实用条件概率表达， 后验也用条件概率来表达， 基于此的贝叶斯定律数学方程极为简单：

![image](https://github.com/whw199833/2021_for_work/blob/master/images/20dc6dd3b18760e89f6be2682c2df0ee_720w.jpg)

贝叶斯分析的思路对于由证据的积累来推测一个事物发生的概率具有重大作用， 它告诉我们当我们要预测一个事物， 我们需要的是首先根据已有的经验和知识推断一个先验概率， 然后在新证据不断积累的情况下调整这个概率。整个通过积累证据来得到一个事件发生概率的过程我们称为贝叶斯分析。

![image](https://github.com/whw199833/2021_for_work/blob/master/images/b31aa378530e552127512be06a522b70.svg)

#### 1.2 全概率公式
全概率就是表示达到某个目的，有多种方式（或者造成某种结果，有多种原因），问达到目的的概率是多少（造成这种结果的概率是多少）？

全概率公式：

    设事件L1 ~ Ln是一个完备事件组，则对于任意一个事件Ｃ，若有如下公式成立：
![image](https://raw.githubusercontent.com/whw199833/2021_for_work/master/images/20170718154223896.gif)

详情可见: https://blog.csdn.net/u010164190/article/details/81043856

### 2. 数据结构-- 排序算法(含快速排序) + 算法复杂度 + 内存很大怎么排序
#### 2.1 排序算法

### 3. 假设检验：简单介绍一下假设检验，有什么用，卡方检验是什么，两者有什么区别，卡方检验和线性回归/皮尔森相关系数有什么区别

### 4. 聚集索引和非聚集索引,什么情况下索引失效

#### 4.1 聚集索引和非聚集索引
聚集索引：存放的物理顺序和列中的顺序一样，一般设置主键索引就为聚集索引。

非聚集索引之间不存在关联。

通过聚集索引可以一次查到需要查找的数据，而非聚集索引第一次只能查到记录对应的主键值，再使用主键的值通过聚集索引查到需要的数据。

两者的根本区别是表记录的排列顺序和与索引的排列顺序是否一致。

1.聚集索引一个表只能有一个，而非聚集索引一个表可以存在多个。（主键的作用就是把表的数据格式转换成索引（平衡树）的格式放置。

2.聚集索引存储记录是物理上连续存在，而非聚集索引是逻辑上的连续，物理存储并不连续。

3.聚集索引查询数据速度快，插入数据速度慢；非聚集索引反之。

详情： https://zhuanlan.zhihu.com/p/86189418

#### 4.2 索引失效

1. 如果mysql认为全表扫面要比使用索引快，则不使用索引。

2. like的模糊查询以%开头，索引失效 

       select * from student where name like 'aaa%'     // 会用到索引

       select * from student where name like '%aaa'        或者   '_aaa'   //  不会使用索引

3. 对于创建的多列索引（复合索引），不是使用的第一部分就不会使用索引

平时用的SQL查询语句一般都有比较多的限制条件，所以为了进一步榨取MySQL的效率，就要考虑建立组合索引。例如上表中针对title和time建立一个组合索引：ALTER TABLE article ADD INDEX index_titme_time (title(50),time(10))。建立这样的组合索引，其实是相当于分别建立了下面两组组合索引：

        –title,time
        –title
        
为什么没有time这样的组合索引呢？这是因为MySQL组合索引“最左前缀”的结果。简单的理解就是只从最左面的开始组合。并不是只要包含这两列的查询都会用到该组合索引

        alter table student add index my_index(name, age)   // name左边的列， age 右边的列                                                              
        select * from student where name = 'aaa'     // 会用到索引

        select * from student where age = 18          //  不会使用索引
       
4. where条件中使用or，索引就会失效，会造成全表扫描：

如果条件中有or，即使其中有条件带索引也不会使用(这也是为什么尽量少用or的原因)

要想使用or，又想让索引生效，只能将or条件中的每个列都加上索引

5. 不等式 <> 或 != 会导致索引失效

6. 类型不一致：字段 key1 为字符串，传入的值为数字类型，会导致索引失效

详情部分：https://yq.aliyun.com/articles/388463

### 5. 深拷贝和浅拷贝

### 6. B+树和B-树

### 7. TCP和UDP

    
## 工具篇:
### 1. SQL 子查询, 子表命名

嵌套SELECT语句也叫子查询，一个 SELECT 语句的查询结果能够作为另一个语句的输入值。子查询不但能够出现在Where子句中，也能够出现在from子句中，作为一个临时表使用，也能够出现在select list中，作为一个字段值来返回。

出现在where中较多,子查询嵌套在where子句中，通常用于对集合成员资格、集合的比较以及集合的基数进行检查。

出现在from子句的子查询后，having就显得不必要，因为having子句使用的谓词出现在外层查询的where子句中，当然，不是说不可以用。

    下面的code中,子表命名为S
    
    SELECT dept_name,avg_salary
    FROM (
      SELECT dept_name,avg(salary) AS avg_salary
      FROM instructor
      GROUP BY dept_name
    )AS S 
    WHERE S.avg_salary>15000;
       
详情可见: https://www.jianshu.com/p/c5d78219abbd

### 2. SQL 左连接右连接全连接,连接表实际怎么做的,关联之间的区别

left join （左连接）：返回包括左表中的所有记录和右表中连接字段相等的记录。

right join （右连接）：返回包括右表中的所有记录和左表中连接字段相等的记录。

inner join （等值连接或者叫内连接）：只返回两个表中连接字段相等的行。

full join （全外连接）：返回左右表中所有的记录和左右表中连接字段相等的记录。

注：在sql中l外连接包括左连接（left join ）和右连接（right join），全外连接（full join），等值连接（inner join）又叫内连接。

### 3. SQL having和where的区别

where 在查询结果集返回之前过滤数据库中的数据, where中不能使用聚合函数.

having 在查询结果集后过滤数据库中的函数, having中可以使用聚合函数.

HAVING子句可以让我们筛选成组后的各组数据，WHERE子句在聚合前先筛选记录．也就是说作用在GROUP BY 子句和HAVING子句前；而 HAVING子句在聚合后对组记录进行筛选。

HAVING语句通常（亲自验证，不是必须！）与GROUP BY语句联合使用，用来过滤由GROUP BY语句返回的记录集。

HAVING语句的存在弥补了WHERE关键字不能与聚合函数联合使用的不足。

*聚合函数:

SQL中提供的聚合函数可以用来统计、求和、求最值等等。
分类：

–COUNT：统计行数量

–SUM：获取单个列的合计值

–AVG：计算某个列的平均值

–MAX：计算列的最大值

–MIN：计算列的最小值


### 4. SQL 主键的选择

主键是能确定一条记录的唯一标识，比如，一条记录包括身份正号，姓名，年龄。身份证号是唯一能确定你这个人的，其他都可能有重复，所以，身份证号是主键。

外键用于与另一张表的关联。是能确定另一张表记录的字段，用于保持数据的一致性。比如，A表中的一个字段，是B表的主键，那他就可以是A表的外键。

    
    --设置主键方法一：
    drop table student    --删除表student
    create table student  --创建表student
    (sno char(4) primary key,  --设置sno为主键
    sname char(8),
    sage int,
    ssex char(2),
    sdept char(20)
    )
    
    --设置主键方法二：
    drop table sc    --删除表sc
    create table sc  --创建表sc
    (sno char(4),
    cno char(4),
    grade int,
    primary key(sno, cno)  --设置sno和cno的属性组为主键
    )
    
    
    --设置外键：
    CREATE TABLE table_name  
    (  
        column1 datatype [ NULL | NOT NULL ],  
        column2 datatype [ NULL | NOT NULL ],  
        ...  
        CONSTRAINT fk_column  
        FOREIGN KEY (column1, column2, ... column_n)  
        REFERENCES parent_table (column1, column2, ... column_n)  
    )
    
    
    --code实例：创建一个以department表作为引用表(父表)拥有外键的 employees 表， employees 表的department_id列引用父表department的department_id列作为外键。    
    -- 父表
    CREATE TABLE departments  
    (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,  
        department_name VARCHAR  
    );  
    -- 拥有外键的表
    CREATE TABLE employees  
    (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,  
        last_name VARCHAR NOT NULL,  
        first_name VARCHAR,  
        department_id INTEGER,  
        CONSTRAINT fk_departments  
        FOREIGN KEY (department_id)  
        REFERENCES departments(department_id)  
    )





### 5. Python 7.python读取文件并排序，用的包和调用的函数
