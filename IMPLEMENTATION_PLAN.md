# majiang_support 实现计划

## 0. 背景

当前产品方向是四川麻将辅助软件，V1 已先实现命令行决策原型，不做图像识别，也不做对手建模。先把核心决策引擎做扎实：

```text
先用规则 + 向听数 + 有效进张做“自己手牌最优出牌”，
再用外面牌和对手行为给每张候选牌加风险折扣，
最后输出综合评分最高的出牌。
```

## 1. 版本路线

### V1：自己手牌最优决策

目标：只看自己的手牌，推荐打哪张。

已实现：

- 川麻牌表示
- 定缺过滤
- 向听数计算
- 有效进张计算
- 搭子质量粗评分
- 候选出牌排序
- 推荐理由生成

V1 当前规则边界：

- 只使用万、筒、条三门牌。
- 默认拒绝字牌，因为四川血战到底常见规则不使用字牌。
- 定缺未完成时，候选出牌限制在缺门牌里。
- 有效进张会排除定缺花色。
- 胡牌和向听只按标准牌型计算，七对等番型留给 V2。

决策顺序：

1. 如果还有缺门牌，只能从缺门牌里选。
2. 枚举每张候选出牌。
3. 计算打出后的向听数。
4. 向听数相同则比较有效进张。
5. 仍相同则比较搭子质量。
6. 输出最高分候选牌。

### V2：牌型 EV 引擎

目标：从“最快胡”升级为“期望收益更高”。

支持候选牌型：

- 平胡
- 对对胡
- 清一色
- 七对
- 龙七对

核心公式：

```text
EV = P(Hu) × Fan × StageFactor
```

第一版概率估计先用近似值：

```text
P(Hu) ≈ 有效进张剩余数量 / 剩余未知牌数量
```

### V3：外面牌统计

目标：让有效进张从“理论数量”变成“真实剩余数量”。

维护：

- 已打出的牌
- 各家碰杠牌
- 自己手牌
- 每张牌已见数量
- 每张牌剩余数量
- 未知牌池总数

例如：

```text
如果 7万 已经出现 3 张，
则 5万6万 的两面搭子价值下降。
```

### V4：对手推断与防守风险

目标：给每张候选出牌加风险折扣。

先做规则模型：

- 对手长期不打某一门：可能保留该门或主攻该门。
- 对手早期打中张：可能定缺或放弃该门。
- 对手连续碰同一门：可能做对对胡或清一色。
- 对手后期突然打安全牌：可能已听牌。

输出：

```text
某张牌点炮风险 =
生张风险
+ 靠近对手可能搭子风险
+ 非对手缺门风险
+ 后期阶段风险
+ 多家同时需要风险
```

### V5：截图识别与实时辅助

目标：减少人工输入。

放在决策引擎稳定之后：

- 截图
- 手动标定手牌区域
- 模板匹配识别牌面
- 低置信度人工确认
- 自动更新牌局状态
- 悬浮窗显示推荐

## 2. 项目结构

```text
majiang_support/
  core/
    tile.py             # 牌编码、解析、排序、花色判断
    hand.py             # 手牌增删、计数、候选出牌
    state.py            # 牌局状态
    rules.py            # 川麻规则入口
    shanten.py          # 向听数计算
    effective.py        # 有效进张计算
    win.py              # 胡牌判断
  strategy/
    discard.py          # V1 出牌推荐
    structure.py        # 搭子质量评分
    pattern.py          # V2 牌型路线识别
    ev.py               # V2 EV 计算
    risk.py             # V4 风险评估
  app/
    cli.py              # 命令行原型
  vision/
    screenshot.py       # 后续截图
    recognizer.py       # 后续牌面识别
  tests/
    test_tile.py
    test_shanten.py
    test_effective.py
    test_discard.py
```

## 3. 数据模型

### 3.1 Tile

第一版需要支持川麻三门牌，字牌可以保留扩展能力，但默认规则不使用。

推荐编码：

```text
1m-9m：一万到九万
1p-9p：一筒到九筒
1s-9s：一条到九条
E/S/W/N/C/F/P：东南西北中发白，扩展用
```

内部编码：

```text
0-8    万
9-17   筒
18-26  条
27+    字牌扩展
```

### 3.2 Hand

职责：

- 解析输入
- 校验张数
- 统计每张牌数量
- 移除候选出牌
- 判断是否包含缺门
- 生成候选出牌集合

### 3.3 GameState

V1 只需要：

- `hand`
- `missing_suit`
- `stage`

V3 之后增加：

- `discards`
- `melds`
- `visible_counts`
- `remaining_counts`
- `unknown_tile_count`
- `opponent_profiles`

## 4. V1 详细算法

### 4.1 定缺过滤

```python
def candidate_discards(hand, missing_suit):
    missing_tiles = [tile for tile in hand if tile.suit == missing_suit]
    if missing_tiles:
        return unique(missing_tiles)
    return unique(hand)
```

### 4.2 向听数

先实现标准牌型：

```text
4 副面子 + 1 对将
```

七对可在 V2 加入。

向听计算目标：

- 输入 13 张或 14 张手牌。
- 输出距离听牌或胡牌还差几步。
- 可用于比较不同候选出牌。

建议实现方式：

1. 使用计数数组表示 27 种牌。
2. DFS 拆分刻子、顺子、对子、搭子。
3. 计算面子数、对子数、搭子数。
4. 得到标准型向听。

### 4.3 有效进张

对打出后的 13 张牌：

```python
base_shanten = calculate_shanten(hand)

for tile in all_tiles:
    if remaining_count(tile) <= 0:
        continue

    next_hand = hand.add(tile)
    next_shanten = calculate_shanten(next_hand)

    if next_shanten < base_shanten:
        useful_tiles.append(tile)
```

V1 没有外面牌时，默认每张最多 4 张，扣除自己手牌中的数量。

输出：

- 有效牌种类
- 有效牌剩余张数
- 摸到后向听数变化

### 4.4 搭子质量

简单评分即可：

| 结构 | 分值 |
| --- | ---: |
| 已成面子 | +8 |
| 对子 | +5 |
| 两面搭子 | +4 |
| 坎张搭子 | +2 |
| 边张搭子 | +1 |
| 孤张中张 | 0 |
| 孤张幺九 | -1 |
| 孤张字牌 | -2 |

### 4.5 出牌评分

```text
评分 = -100 × 向听数 + 有效进张剩余张数 + 搭子质量分
```

候选结果结构：

```python
{
    "discard": "白",
    "score": -174,
    "shanten": 2,
    "effective_tile_count": 18,
    "structure_score": 8,
    "reasons": [
        "白是孤张，无法组成顺子",
        "打出后向听数保持最低",
        "有效进张数量更多"
    ]
}
```

## 5. V2 牌型 EV

### 5.1 候选路线识别

系统看到手牌后分析距离哪些牌型最近：

```python
[
    PingHu,
    DuiDuiHu,
    QingYiSe,
    QiDui,
    LongQiDui,
]
```

每条路线至少要输出：

- `distance_to_pattern`
- `effective_tiles`
- `remaining_effective_count`
- `fan`
- `ev`
- `reason`

### 5.2 完成难度

示例：

```text
平胡：距离 1，有效进张 18 张
对对胡：距离 2，有效进张 8 张
清一色：距离 3，有效进张 6 张
龙七对：距离 4，有效进张 4 张
```

### 5.3 阶段因子

```python
STAGE_FACTOR = {
    "early": 1.15,
    "middle": 1.0,
    "late": 0.75,
}
```

解释：

- 开局牌墙多，可以适当贪清一色、七对、龙七对。
- 中盘进攻和现实性平衡。
- 末盘有胡就胡，降低做大牌权重。

## 6. V3 外面牌统计

V3 要把“有效进张种类数”升级为“有效进张剩余张数”。

```python
remaining_count(tile) = 4 - self_count(tile) - visible_count(tile)
```

可见牌包括：

- 自己手牌
- 自己已打
- 对手已打
- 所有碰杠

如果某张有效牌已经全部出现，则不再计入有效进张。

## 7. V4 风险模型

### 7.1 对手 Profile

每个对手维护：

- 可能缺门
- 可能主攻花色
- 是否可能听牌
- 碰杠倾向
- 最近出牌
- 危险花色

### 7.2 点炮风险评分

```text
risk =
  生张风险
  + 对手主攻花色风险
  + 靠近对手可能搭子风险
  + 后期阶段风险
  + 多家需要风险
  - 已现安全牌折扣
```

最终综合：

```text
综合评分 = 进攻价值 - 点炮风险 + 番型潜力
```

## 8. CLI MVP

第一版命令行可以这样使用：

```text
majiang recommend \
  --hand "1m 2m 3m 5m 6m 8m 8m 2p 3p 4p E E P" \
  --missing p \
  --stage middle
```

输出：

```text
推荐出牌：P

候选评分：
P   score=-174 shanten=2 effective=18 structure=8
8m  score=-273 shanten=3 effective=22 structure=5
E   score=-285 shanten=3 effective=10 structure=5

理由：
1. P 是孤张字牌，无法组成顺子。
2. 打出 P 后向听数最低。
3. 保留 5m6m、8m8m 和 E E 的结构价值更高。
```

## 9. 测试计划

### V1 必须测试

- 牌解析和排序
- 定缺过滤
- 标准胡牌判断
- 标准向听数
- 有效进张枚举
- 候选出牌评分
- 推荐理由生成

### 关键样例

```text
1m 2m 3m 5m 6m 8m 8m 2p 3p 4p E E P
```

期望：

- 如果缺筒且仍有筒牌，则只能从筒牌里选。
- 如果不考虑缺门，孤张白应比拆 8m 对子更优先打出。

## 10. 里程碑

### M0：文档与仓库初始化

- README
- 实现计划
- 明确 V1 范围

### M1：核心数据结构

- Tile
- Hand
- GameState
- 基础测试

### M2：规则计算

- 胡牌判断
- 标准向听数
- 有效进张
- 定缺过滤

### M3：推荐引擎

- 候选出牌评分
- 搭子质量评分
- 推荐理由
- CLI 原型

### M4：EV 引擎

- 牌型路线识别
- 番数配置
- EV 计算
- 阶段因子

### M5：外面牌和风险

- 可见牌统计
- 剩余牌统计
- 对手 Profile
- 点炮风险评分

### M6：截图识别

- 截图
- 区域标定
- 模板匹配
- 人工纠错

## 11. 当前下一步

建议从 M1 开始：

1. 初始化 Python 项目。
2. 实现 `Tile` 和输入解析。
3. 实现 `Hand` 计数和候选出牌。
4. 实现定缺过滤。
5. 加第一批 pytest。
6. 再进入向听数和有效进张。
