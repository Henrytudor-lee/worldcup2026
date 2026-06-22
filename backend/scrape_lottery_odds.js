#!/usr/bin/env node
/**
 * 竞彩赔率抓取器
 * 从中国体彩网 (lottery.gov.cn) 实时抓取胜平负 & 让球胜平负赔率
 * 用法: node scrape_lottery_odds.js
 */

const { chromium } = require('playwright');

async function scrapeLotteryOdds() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('正在访问体彩网赔率页面...');
  await page.goto('https://www.lottery.gov.cn/jc/jsq/zqspf/', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  // Wait for table to render
  await page.waitForSelector('table tr', { timeout: 10000 });
  await page.waitForTimeout(2000);

  console.log('正在提取赔率数据...');
  const matches = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('table tr').forEach(tr => {
      const tds = Array.from(tr.querySelectorAll('td'));
      if (tds.length < 6) return;

      // Extract team names from HTML (VS might be in a different cell)
      const cells = tds.map(td => td.innerHTML.trim());
      const teamHtml = cells[3] || '';
      if (teamHtml.indexOf('VS') === -1) return;

      // Parse team names by stripping HTML tags and group labels
      const tmp = document.createElement('div');
      tmp.innerHTML = teamHtml;
      const txt = tmp.textContent.replace(/\s+/g, ' ').trim();
      const parts = txt.split(' VS ');
      if (parts.length !== 2) return;

      const home = parts[0].replace(/\[.+?\]/g, '').trim();
      const away = parts[1].replace(/\[.+?\]/g, '').trim();
      if (!home || !away) return;

      const rawCode = cells[0].replace('<br>', '').trim();
      if (!rawCode || rawCode.includes('赛事编号') || rawCode.includes('主队') || !rawCode.match(/\d{3}/)) return;

      const match = {
        home,
        away,
        code: rawCode,
      };

      // 胜平负 status (0=normal, 未开售=not available)
      const hadDiv = tds[4].querySelector('div[title="胜平负"]');
      match.had_status = hadDiv ? hadDiv.textContent.trim() : '0';
      match.had_available = match.had_status !== '未开售';

      // 让球状态
      const hhadDiv = tds[4].querySelector('div[title="让球胜平负"]');
      match.hhad_status = hhadDiv ? hhadDiv.textContent.trim() : '';
      match.hhad_handicap = parseInt(match.hhad_status) || 0;

      // 胜平负赔率
      const hadOddsDiv = tds[5].querySelector('div.hadOdds');
      if (hadOddsDiv) {
        const spans = Array.from(hadOddsDiv.querySelectorAll('span'));
        if (spans.length >= 3) {
          const h = parseFloat(spans[0].textContent);
          const d = parseFloat(spans[1].textContent);
          const a = parseFloat(spans[2].textContent);
          if (!isNaN(h) && !isNaN(d) && !isNaN(a)) {
            match.had = { home: h, draw: d, away: a };
          }
        }
      }

      // 让球胜平负赔率
      const hhadOddsDiv = tds[5].querySelector('div.hhadOdds');
      if (hhadOddsDiv) {
        const spans = Array.from(hhadOddsDiv.querySelectorAll('span'));
        if (spans.length >= 3) {
          const h = parseFloat(spans[0].textContent);
          const d = parseFloat(spans[1].textContent);
          const a = parseFloat(spans[2].textContent);
          if (!isNaN(h) && !isNaN(d) && !isNaN(a)) {
            match.hhad = { home: h, draw: d, away: a };
          }
        }
      }

      out.push(match);
    });
    return out;
  });

  await browser.close();

  // Print summary
  const had_available = matches.filter(m => m.had_available).length;
  const hhad_available = matches.filter(m => m.hhad && Object.keys(m.hhad).length > 0).length;

  console.log(`\n✅ 抓取成功！共 ${matches.length} 场比赛`);
  console.log(`   胜平负开售: ${had_available} 场`);
  console.log(`   让球胜平负开售: ${hhad_available} 场`);
  console.log('\n详细数据:');
  matches.forEach(m => {
    const hadStr = m.had_available && m.had
      ? `胜平负 ${m.had.home}/${m.had.draw}/${m.had.away}`
      : '胜平负 未开售';
    const hhadStr = m.hhad
      ? `让球${m.hhad_status} ${m.hhad.home}/${m.hhad.draw}/${m.hhad.away}`
      : '让球 未开售';
    console.log(`  ${m.code} ${m.home} vs ${m.away}: ${hadStr}, ${hhadStr}`);
  });

  return matches;
}

scrapeLotteryOdds()
  .then(matches => {
    const fs = require('fs');
    const path = require('path');
    const outputPath = path.join(__dirname, '..', '1_数据基础', 'lottery_odds_live.json');
    const data = {
      scraped_at: new Date().toISOString().replace('Z', '+00:00'),
      source: 'https://www.lottery.gov.cn/jc/jsq/zqspf/',
      matches
    };
    fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), 'utf-8');
    console.log(`\n💾 已保存到 ${outputPath}`);
  })
  .catch(err => {
    console.error('❌ 抓取失败:', err.message);
    process.exit(1);
  });
