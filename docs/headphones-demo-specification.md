# 🎧 蓝牙耳机品类 Demo 规格文档

## 📋 项目概述

本文档详细说明了基于蓝牙耳机品类的Amazon产品追踪系统Demo实现方案，包括爬虫配置、产品选择、数据结构等关键信息。

## 🎯 选择理由

**蓝牙耳机品类优势:**
- ✅ **BSR数据完整性**: 100%可获取
- ✅ **数据丰富度**: 多层级排名（Electronics > Over-Ear/Earbud Headphones）
- ✅ **价格范围广**: $20-$600，适合价格监控
- ✅ **竞争激烈**: Apple, Sony, Bose, Anker等知名品牌
- ✅ **特征明显**: 降噪、电池续航、音质等可对比维度
- ✅ **更新频繁**: 产品迭代快，适合实时监控

## 🔧 爬虫配置

### 主要爬虫 (产品详情)
```json
{
  "actor_id": "ZhSGsaq9MHRnWtStl",
  "actor_name": "junglee/amazon-asins-scraper", 
  "input_format": {
    "asins": ["B0D1XD1ZV3", "B08PZHYWJS", "..."],
    "amazonDomain": "amazon.com",
    "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
    "useCaptchaSolver": false
  },
  "output_features": [
    "bestsellerRanks (94.6%可用率)",
    "price", "buyBoxUsed.price", 
    "productRating", "countReview",
    "features", "productDetails",
    "seller", "availability"
  ]
}
```

### 辅助爬虫 (BSR排行榜)
```json
{
  "actor_id": "junglee/amazon-bestsellers",
  "actor_name": "Amazon Bestsellers Scraper",
  "input_format": {
    "categoryUrls": [
      "https://www.amazon.com/Best-Sellers-Electronics-Headphones/zgbs/electronics/12097478011",
      "https://www.amazon.com/Best-Sellers-Electronics-Earbud-Headphones/zgbs/electronics/12097479011"
    ],
    "maxItems": 50,
    "country": "US"
  },
  "output_features": [
    "position (BSR排名)",
    "asin", "name", "price",
    "stars", "reviewsCount",
    "categoryName", "categoryFullName"
  ]
}
```

## 📱 Demo产品清单 (20个)

### 🏆 主流品牌产品 (15个)

#### Apple系列 (4个)
1. **B0D1XD1ZV3** - Apple AirPods Pro 2 (2024)
   - 价格: $199 | BSR: #1 in Earbud Headphones
   - 特征: H2芯片, 主动降噪, 助听功能

2. **B09JQMJHXY** - Apple AirPods Pro (1st Gen) with MagSafe
   - 价格: $178-$238 | 评分: 4.7/5 (147,913评论)
   - 特征: H1芯片, 主动降噪, 透明模式

3. **B08PZHYWJS** - Apple AirPods Max
   - 价格: $403-$599 | 评分: 4.5/5 (8,170评论)
   - 特征: 头戴式, 计算音频, 空间音频

4. **B0CHWRXH8B** - Apple AirPods (3rd Generation)
   - 价格: $129-$179 | 入门级选择
   - 特征: 空间音频, 防汗抗水

#### Sony系列 (4个)
5. **B0863TXGM3** - Sony WH-1000XM4 (Black)
   - 价格: $170-$320 | 评分: 4.6/5 (60,925评论)
   - 特征: 30小时续航, 智能降噪

6. **B08MVGF24M** - Sony WH-1000XM4 (Midnight Blue)
   - 价格: $176-$275 | 同系列不同颜色
   - 特征: 快速充电, 多点连接

7. **B0C33XXS56** - Sony WH-1000XM5
   - 价格: $328-$399 | 最新旗舰
   - 特征: 8个麦克风, 改进设计

8. **B09FC1PG9H** - Sony WF-1000XM4 (真无线)
   - 价格: $199-$279 | 真无线旗舰
   - 特征: LDAC编解码, 8小时续航

#### Bose系列 (3个)
9. **B0756CYWWD** - Bose QuietComfort 35 II
   - 价格: $199-$299 | BSR: #1728 in Over-Ear
   - 特征: 经典降噪, Alexa内置

10. **B08YRM5D7X** - Bose QuietComfort Earbuds
    - 价格: $179-$279 | 真无线降噪
    - 特征: 11级降噪调节

11. **B09NQBL7SF** - Bose QuietComfort 45
    - 价格: $229-$329 | 新一代头戴式
    - 特征: 24小时续航, 改进舒适度

#### 其他品牌 (4个)
12. **B07ZPKN6YR** - Anker Soundcore Life Q30
    - 价格: $55-$79 | 性价比之选
    - 特征: 混合主动降噪, 40小时续航

13. **B08HMWZBXC** - Jabra Elite 85h
    - 价格: $149-$249 | 商务首选
    - 特征: 智能声音, 防雨防尘

14. **B08QJ2KGSP** - Sennheiser Momentum 3 Wireless
    - 价格: $249-$399 | 音质专业
    - 特征: 真皮材质, 自适应降噪

15. **B0856BFBXZ** - Audio-Technica ATH-M50xBT2
    - 价格: $149-$199 | 专业监听
    - 特征: 50mm驱动器, 低延迟

### 🚀 新兴品牌产品 (5个)

16. **B093MBYX7P** - Nothing Ear (stick)
    - 价格: $79-$99 | 设计创新
    - 特征: 透明设计, 半开放式

17. **B09K7S1HKZ** - Beats Studio Buds+
    - 价格: $129-$179 | Apple生态
    - 特征: 空间音频, 透明度模式

18. **B08T7BQMGG** - Skullcandy Crusher ANC
    - 价格: $159-$219 | 重低音
    - 特征: 可调节低音, 24小时续航

19. **B08R7YP5KB** - Marshall Major IV
    - 价格: $99-$149 | 复古风格
    - 特征: 80小时续航, 可折叠

20. **B09JB4DCTM** - 1MORE ComfoBuds Pro
    - 价格: $59-$89 | 入门降噪
    - 特征: 主动降噪, 舒适佩戴

## 📊 数据结构定义

### 产品基础数据
```json
{
  "asin": "B0D1XD1ZV3",
  "title": "Apple AirPods Pro 2 Wireless Earbuds...",
  "brand": "Apple",
  "manufacturer": "Apple",
  "category": "蓝牙耳机",
  "marketplace": "amazon_us",
  "product_url": "https://www.amazon.com/dp/B0D1XD1ZV3",
  "image_url": "https://images-na.ssl-images-amazon.com/...",
  "is_main_product": false,
  "is_competitor": true
}
```

### 价格数据
```json
{
  "current_price": 199.00,
  "list_price": 249.00,
  "buy_box_price": 199.00,
  "currency": "USD",
  "price_offers": [
    {
      "seller": "Amazon",
      "price": 199.00,
      "condition": "New",
      "shipping": "Free"
    }
  ]
}
```

### BSR排名数据
```json
{
  "bestsellerRanks": [
    {
      "rank": 1,
      "category": "Earbud Headphones",
      "url": "https://www.amazon.com/gp/bestsellers/electronics/12097479011/"
    },
    {
      "rank": 15,
      "category": "Electronics",
      "url": "https://www.amazon.com/gp/bestsellers/electronics/"
    }
  ]
}
```

### 评价数据
```json
{
  "current_rating": 4.6,
  "current_review_count": 37658,
  "stars_breakdown": {
    "5_star": 68,
    "4_star": 19,
    "3_star": 7,
    "2_star": 3,
    "1_star": 3
  }
}
```

### 产品特征数据
```json
{
  "features": [
    "Active Noise Cancellation blocks outside noise",
    "Transparency mode for hearing your surroundings",
    "Personalized Spatial Audio with dynamic head tracking",
    "Up to 6 hours of listening time with ANC enabled"
  ],
  "product_details": [
    {
      "name": "Connectivity Technology",
      "value": "Wireless, Bluetooth"
    },
    {
      "name": "Battery Life",
      "value": "Up to 6 hours"
    },
    {
      "name": "Noise Control",
      "value": "Active Noise Cancellation"
    }
  ]
}
```

## 🎯 竞品分析维度

### 价格竞争力
- **价格区间分析**: $59-$599
- **价格变化监控**: 日变化率 > 10%触发预警
- **Buy Box竞争**: 多卖家价格对比

### BSR排名竞争
- **主类别排名**: Electronics分类
- **子类别排名**: Earbud/Over-Ear Headphones
- **排名变化预警**: BSR变动 > 30%触发通知

### 用户评价对比
- **评分对比**: 4.0-4.8分区间
- **评论数量**: 100-150k评论范围
- **评价趋势**: 月度评分变化

### 产品特征对比
- **核心功能**: 降噪、续航、音质
- **连接技术**: 蓝牙版本、编解码器
- **使用场景**: 运动、通勤、办公

## 🔄 监控策略

### 数据更新频率
- **价格监控**: 每日更新
- **BSR排名**: 每日更新
- **评价数据**: 每周更新
- **产品特征**: 月度更新

### 异常预警阈值
- **价格变动**: >10%
- **BSR排名变动**: >30%
- **评分变化**: >0.2分
- **库存状态**: 缺货通知

## 📈 预期效果

### Demo展示能力
1. **实时价格监控**: 20个产品的价格趋势
2. **BSR排名追踪**: 多层级排名变化
3. **竞品分析报告**: AI生成的市场洞察
4. **异常预警系统**: 自动化监控通知
5. **数据可视化**: 竞争态势图表

### 技术验证点
1. **爬虫稳定性**: 94.6% BSR数据可用率
2. **数据完整性**: 多维度产品信息
3. **系统扩展性**: 支持1000+产品规模
4. **实时性能**: 每日定时更新机制

---

**文档版本**: v1.0  
**更新时间**: 2025-09-13  
**负责人**: Amazon产品追踪系统开发团队