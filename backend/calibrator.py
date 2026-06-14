"""
Mavis PDP 评估 + 校准器 (v2.2)

职责:
  1. evaluate(weights) - 用 match_results.csv 评估当前 weights
     - W/D/L 命中率
     - 比分距离 (MAE)
     - 详细每场对比
  2. calibrate(n_iter=20) - 贝叶斯优化 (scikit-optimize) 自动调 weights
  3. 校准历史持久化 → calibration_history.json

设计:
  - 校准目标: 最大化 W/D/L 命中率, 同时最小化比分 MAE
  - 综合得分 = 命中率 * 100 - MAE * 5
  - 网格搜索兜底 (scikit-optimize 不可用时)
"""
import csv
import json
import math
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "1_数据基础"
CSV_RESULTS = DATA_DIR / "match_results.csv"
CALIB_HISTORY = PROJECT_ROOT / "5_算法" / "calibration_history.json"
CALIB_BEST = PROJECT_ROOT / "5_算法" / "calibration_best.json"


def load_results():
    """读 match_results.csv → [(date, home, away, hs, as), ...]"""
    if not CSV_RESULTS.exists():
        return []
    results = []
    with open(CSV_RESULTS, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                results.append((
                    row['date'],
                    row['home'],
                    row['away'],
                    int(row['home_score']),
                    int(row['away_score']),
                ))
            except (ValueError, KeyError):
                continue
    return results


def evaluate(weights, verbose=True):
    """用当前 weights 重算所有比赛, 对比真实结果

    返回: {
        'match_count': N,
        'win_correct': 命中的 W/D/L 数,
        'win_accuracy': 命中率 0~1,
        'score_mae': 比分平均绝对误差 (主+客 / 2),
        'score_correct': 完全命中比分 (best_score == actual) 数,
        'details': [{date, home, away, predicted, actual, wdl_correct, score_diff}, ...]
        'champion': 当前 weights 预测的冠军名字 (从 compute_predictions.final.winner)
        'runner_up': 亚军
        'third_place': 季军
        'loss': 损失值 (越低越好) = -accuracy * 100 + mae * 5
    }
    """
    import predictor

    results = load_results()
    if not results:
        return {'error': 'no match results yet'}

    # 跑全 104 场预测
    pred = predictor.compute_predictions(weights)
    # 索引: (home, away) → pred (注意预测里是中文队名, results 也是中文)
    pred_index = {}
    for p in pred['predictions']:
        pred_index[(p['home'], p['away'])] = p

    win_correct = 0
    score_diff_sum = 0
    score_correct = 0
    details = []
    matched = 0
    for date, h, a, hs, as_ in results:
        if (h, a) not in pred_index:
            continue
        matched += 1
        p = pred_index[(h, a)]
        # 预测 W/D/L
        pred_h, pred_a = [int(x) for x in p['best_score'].split('-')]
        pred_wdl = 'W' if pred_h > pred_a else ('D' if pred_h == pred_a else 'L')
        actual_wdl = 'W' if hs > as_ else ('D' if hs == as_ else 'L')
        wdl_correct = pred_wdl == actual_wdl
        # 比分距离
        score_diff = abs(pred_h - hs) + abs(pred_a - as_)
        if wdl_correct:
            win_correct += 1
        if score_diff == 0:
            score_correct += 1
        score_diff_sum += score_diff
        details.append({
            'date': date, 'home': h, 'away': a,
            'predicted': f'{pred_h}-{pred_a}', 'actual': f'{hs}-{as_}',
            'pred_wdl': pred_wdl, 'actual_wdl': actual_wdl,
            'wdl_correct': wdl_correct,
            'score_diff': score_diff,
            'p_home_win': p.get('p_home_win', 0),
            'p_draw': p.get('p_draw', 0),
            'p_away_win': p.get('p_away_win', 0),
        })

    if matched == 0:
        return {'error': f'no matches in results match predictions (results={len(results)})'}

    accuracy = win_correct / matched
    mae = score_diff_sum / matched
    # 损失: 命中率优先, 比分次之
    # loss = -accuracy * 100 + mae * 5
    loss = -accuracy * 100 + mae * 5

    if verbose:
        print(f"\n=== 评估结果 ===")
        print(f"  对比场次: {matched}")
        print(f"  W/D/L 命中率: {accuracy:.1%} ({win_correct}/{matched})")
        print(f"  比分 MAE: {mae:.2f}")
        print(f"  比分完全命中: {score_correct} 场")
        print(f"  综合 loss: {loss:.2f}")

    # v2.2.3 顺便算当前 weights 预测的冠军/亚军/季军 (校准实时展示用)
    champion = runner_up = third_place = '?'
    try:
        full_pred = predictor.compute_predictions(weights)
        champion = full_pred.get('final', {}).get('winner', '?')
        runner_up = full_pred.get('final', {}).get('loser', '?')
        third_place = full_pred.get('third_place', {}).get('winner', '?')
    except Exception:
        pass

    return {
        'match_count': matched,
        'win_correct': win_correct,
        'win_accuracy': round(accuracy, 4),
        'score_mae': round(mae, 3),
        'score_correct': score_correct,
        'loss': round(loss, 3),
        'details': details,
        'champion': champion,
        'runner_up': runner_up,
        'third_place': third_place,
    }


def calibrate(n_iter=20, use_bayes=True, verbose=True, log_callback=None):
    """贝叶斯优化 weights

    调 23 固定系数 (略过 _dynamic_weights, 因为 30 动态因子 = 80+ 参数, 4 场样本不够)
    优化目标: minimize(loss) = -accuracy*100 + mae*5

    use_bayes=True 用 scikit-optimize gp_minimize
    use_bayes=False 网格搜索兜底

    log_callback: 可选函数, 接收 (level, message) 字符串
                  level: 'info' / 'iter' / 'best' / 'done' / 'error'
                  用于实时推日志到前端 (SSE)
    """
    from weights_schema import DEFAULT, RANGES, validate, merge_with_default

    def log(level, msg):
        if verbose:
            print(f"  [{level}] {msg}")
        if log_callback:
            try:
                log_callback(level, msg)
            except Exception:
                pass  # 回调出错不影响主流程

    history = load_history()
    base_eval = evaluate(DEFAULT, verbose=False)
    if 'error' in base_eval:
        log('error', f"评估失败: {base_eval['error']}")
        return {'error': base_eval['error']}

    log('info', f"🎯 启动贝叶斯校准 (n_iter={n_iter}, method={'bayes' if use_bayes else 'grid'})")
    log('info', f"  起始 loss: {base_eval['loss']:.2f}, accuracy: {base_eval['win_accuracy']:.1%}")

    # 1. 准备搜索空间: 23 个固定系数
    space = []
    param_names = []
    for group_key, group in RANGES.items():
        if isinstance(group, tuple):
            # 顶层 scalar (e.g. venue_adaptation_weight)
            lo, hi = group
            space.append((lo, hi))
            param_names.append(group_key)
        else:
            for k, (lo, hi) in group.items():
                space.append((lo, hi))
                param_names.append(f'{group_key}.{k}')

    # 2. 参数 ↔ weights 转换
    # position_top_n 字段是 int, 其他都是 float
    INT_FIELDS = {('position_top_n', 'FW'), ('position_top_n', 'MID'),
                  ('position_top_n', 'DEF'), ('position_top_n', 'GK')}

    def params_to_weights(params):
        """params 列表 → weights dict
        约束: player_share + coach_share = 1 (validate 强制)
        解法: 用 player_share 当主参数, coach_share = 1 - player_share

        全部转 native Python 类型, 避免 numpy 标量在 JSON 序列化 / 数值比较时炸
        """
        # 找 player_share / coach_share 在 params 里的索引
        ps_idx = cs_idx = None
        for i, name in enumerate(param_names):
            if name == 'player_to_total.player_share': ps_idx = i
            if name == 'player_to_total.coach_share': cs_idx = i

        w = deepcopy(DEFAULT)
        for i, name in enumerate(param_names):
            v = params[i]
            # coach_share 由 player_share 决定, 跳过直接赋值
            if i == cs_idx:
                continue
            if '.' in name:
                g, k = name.split('.', 1)
                # int 字段 (position_top_n.*) 要 round
                if (g, k) in INT_FIELDS:
                    w[g][k] = max(1, int(round(float(v))))
                else:
                    w[g][k] = float(v)
            else:
                w[name] = float(v)

        # 强制 player_share + coach_share = 1
        if ps_idx is not None:
            w['player_to_total']['player_share'] = float(params[ps_idx])
            w['player_to_total']['coach_share'] = 1.0 - float(params[ps_idx])
        return w

    def eval_loss(params):
        w = params_to_weights(params)
        ok, _ = validate(w)
        if not ok:
            return 100  # 极端值返回大 loss
        # 防 0 除: smoothing 分母必须 >= 100 (留缓冲, 避免接近 0 时 numpy 静默 Inf/NaN)
        for k in ('player_div', 'coach_div', 'rank_div'):
            if w['smoothing'].get(k, 0) < 100:
                return 100
        # lambda_cap 边界: 不能 < 2.5 (过小没意义) 也不能 > 5 (太大)
        if w.get('lambda_cap', 3.5) < 2.5 or w.get('lambda_cap', 3.5) > 5.0:
            return 100
        try:
            ev = evaluate(w, verbose=False)
            if 'error' in ev:
                return 100
            # 防 NaN/Inf (numpy 静默 0/0 不抛异常, 但会污染 loss)
            loss = ev.get('loss')
            if loss is None or not (-1000 < loss < 1000):
                return 100
            return loss
        except Exception as e:
            if verbose:
                print(f"  [err] {e}")
            return 100

    # 3. 选 optimizer
    best_loss = base_eval['loss']
    best_weights = deepcopy(DEFAULT)
    best_iter = -1
    all_iterations = []

    if use_bayes:
        try:
            from skopt import gp_minimize

            # 进度回调: 每次 eval_loss 完成后推一条消息给前端
            _iter_count = [0]  # 闭包变量
            def _skopt_callback(res):
                _iter_count[0] += 1
                i = _iter_count[0]
                # res.func_vals 是 numpy 数组, 不能用 if 判 truth value
                fv = list(res.func_vals) if len(res.func_vals) > 0 else []
                cur_loss = float(fv[-1]) if fv else 100
                best_so_far = float(min(fv)) if fv else 100
                # 算当前 best params 预测的冠军 (取 best_x_iters, 跑一次)
                try:
                    if i == 1 or i % 5 == 0 or cur_loss == best_so_far:
                        # 第一轮 + 每 5 轮 + 新 best 时算冠军 (避免每轮都算)
                        best_idx = int(fv.index(best_so_far)) if fv else 0
                        if 0 <= best_idx < len(res.x_iters):
                            bw = params_to_weights(list(res.x_iters[best_idx]))
                            be = evaluate(bw, verbose=False)
                            # evaluate 内部已经算好 champion/runner_up/third_place
                            champ = be.get('champion', '?')
                            runner = be.get('runner_up', '?')
                            third = be.get('third_place', '?')
                            log('iter', f"iter {i}/{n_iter}: loss={cur_loss:.2f} best={best_so_far:.2f} 🏆最佳预测: 冠军={champ} 亚军={runner} 季军={third}")
                            return
                except Exception:
                    pass
                log('iter', f"iter {i}/{n_iter}: loss={cur_loss:.2f} best={best_so_far:.2f}")

            result = gp_minimize(
                eval_loss,
                space,
                n_calls=n_iter,
                n_initial_points=min(10, n_iter // 2),
                random_state=42,
                verbose=False,
                callback=_skopt_callback,  # 实时推日志
            )
            # 收集每次迭代
            for i, (loss, params) in enumerate(zip(result.func_vals, result.x_iters)):
                w = params_to_weights(params)
                ev = evaluate(w, verbose=False)
                all_iterations.append({
                    'iter': i,
                    'loss': round(float(loss), 3),
                    'accuracy': ev.get('win_accuracy', 0),
                    'mae': ev.get('score_mae', 0),
                    'params': {name: round(p, 4) for name, p in zip(param_names, params)},
                })
                if loss < best_loss:
                    best_loss = loss
                    best_weights = w
                    best_iter = i
                # 实时日志
                log('iter', f"iter {i+1}/{len(result.func_vals)}: loss={loss:.2f} acc={ev.get('win_accuracy',0):.0%} mae={ev.get('score_mae',0):.2f} {'🏆 NEW BEST' if loss == best_loss else ''}")
        except ImportError:
            if verbose:
                print("  [warn] scikit-optimize 未装, 改用网格搜索")
            use_bayes = False

    if not use_bayes:
        # 网格搜索兜底: 每个参数取 2 档 (lo, hi) = 2^23 太大, 改用随机采样
        from itertools import product
        import random
        random.seed(42)
        n_random = min(n_iter, 30)  # 随机采 30 组
        if verbose:
            print(f"  [info] 网格搜索: 随机采样 {n_random} 组 (替代 2^N 全网格)")

        # 找 player_share / coach_share 在 space 里的索引 (互斥约束: 合计=1)
        ps_idx = None
        cs_idx = None
        for i, name in enumerate(param_names):
            if name == 'player_to_total.player_share': ps_idx = i
            if name == 'player_to_total.coach_share': cs_idx = i

        for i in range(n_random):
            # 独立采样
            combo = [random.uniform(lo, hi) for lo, hi in space]
            # 约束修复: coach_share = 1 - player_share (强制 validate 通过)
            if ps_idx is not None and cs_idx is not None:
                # 把 player_share 夹到合法范围, 然后让 coach_share = 1 - player_share
                ps_lo, ps_hi = space[ps_idx]
                cs_lo, cs_hi = space[cs_idx]
                combo[ps_idx] = random.uniform(ps_lo, ps_hi)
                combo[cs_idx] = 1.0 - combo[ps_idx]
                # 也要夹到 cs 的合法范围 (如果超出, 微微向内)
                combo[cs_idx] = max(cs_lo, min(cs_hi, combo[cs_idx]))
                # 此时 ps 可能因为夹 cs 而越界 → 微调
                combo[ps_idx] = 1.0 - combo[cs_idx]
                combo[ps_idx] = max(ps_lo, min(ps_hi, combo[ps_idx]))
                combo[cs_idx] = 1.0 - combo[ps_idx]

            loss = eval_loss(combo)
            w = params_to_weights(combo)
            ev = evaluate(w, verbose=False)
            all_iterations.append({
                'iter': i,
                'loss': round(loss, 3),
                'accuracy': ev.get('win_accuracy', 0),
                'mae': ev.get('score_mae', 0),
                'params': {name: round(p, 4) for name, p in zip(param_names, combo)},
            })
            is_new_best = loss < best_loss
            if is_new_best:
                best_loss = loss
                best_weights = w
                best_iter = i
            # 实时日志: 每轮显示当前配置预测的冠军 + 季军
            champ = ev.get('champion', '?')
            runner = ev.get('runner_up', '?')
            third = ev.get('third_place', '?')
            mark = ' 🏆 NEW BEST' if is_new_best else ''
            log('iter', f"iter {i+1}/{n_random}: loss={loss:.2f} acc={ev.get('win_accuracy',0):.0%} mae={ev.get('score_mae',0):.2f} 冠军={champ} 亚军={runner} 季军={third}{mark}")

    # 4. 保存历史
    def to_native(obj):
        """numpy int64/float64 → Python int/float (避免 JSON 序列化失败)"""
        if hasattr(obj, 'item'):
            return obj.item()
        if isinstance(obj, dict):
            return {k: to_native(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [to_native(v) for v in obj]
        return obj

    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'n_iter': n_iter,
        'method': 'bayes' if use_bayes else 'grid',
        'base_loss': to_native(base_eval['loss']),
        'best_loss': to_native(best_loss),
        'best_iter': to_native(best_iter),
        'improvement': to_native(round(base_eval['loss'] - best_loss, 3)),
        'best_weights': to_native(best_weights),
        'iterations': to_native(all_iterations),
    }
    history.append(record)
    save_history(history)
    save_best(best_weights, best_loss)

    if verbose:
        print(f"\n=== 校准完成 ===")
        print(f"  起始 loss: {base_eval['loss']:.2f}")
        print(f"  最终 loss: {best_loss:.2f}")
        print(f"  改善: {base_eval['loss'] - best_loss:.2f} ({base_eval['loss'] - best_loss:.2f} 减少)")
        print(f"  最佳 iter: #{best_iter}")
        print(f"  历史已存: {CALIB_HISTORY}")

    log('done', f"✅ 校准完成: loss {base_eval['loss']:.2f} → {best_loss:.2f} (改善 {base_eval['loss'] - best_loss:.2f}), 最佳 iter #{best_iter}")
    log('done', f"  history_count: {len(history)}, best_weights 已存盘 → 5_算法/calibration_best.json")
    # 概要 best_weights 关键参数 (前端弹窗展示)
    bw = best_weights
    try:
        log('done', f"  🏆 最佳配置概要: FW={bw['position_top_n']['FW']} MID={bw['position_top_n']['MID']} DEF={bw['position_top_n']['DEF']} GK={bw['position_top_n']['GK']}")
        log('done', f"  · 持球率档位: 1-4名={bw['possession']['rank_tier1']:.0%} 5-8名={bw['possession']['rank_tier2']:.0%} 9-16名={bw['possession']['rank_tier3']:.0%}")
        log('done', f"  · 球员/教练占比: {bw['player_to_total']['player_share']:.0%} / {bw['player_to_total']['coach_share']:.0%}")
        log('done', f"  · λ 上限: {bw.get('lambda_cap', 3.5):.2f} (默认 3.5)")
        log('done', f"  · 阵容深度惩罚: std/mean 阈值={bw['depth']['squad_std_threshold']:.2f} 系数={bw['depth']['squad_std_penalty']:.2f}")
    except Exception as e:
        log('warn', f'best_weights 概要展示失败: {e}')

    return {
        'base_loss': base_eval['loss'],
        'best_loss': best_loss,
        'best_weights': best_weights,
        'best_iter': best_iter,
        'iterations': all_iterations,
        'history_count': len(history),
    }


def load_history():
    """读校准历史 (空则返 [])"""
    if CALIB_HISTORY.exists():
        try:
            with open(CALIB_HISTORY, encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history):
    """保存校准历史"""
    CALIB_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(CALIB_HISTORY, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_best(weights, loss):
    """保存最佳 weights (供 server.py 启动时加载)"""
    CALIB_BEST.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'loss': loss,
        'weights': weights,
    }
    with open(CALIB_BEST, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def get_calibration_summary():
    """返校准摘要 (前端展示用)"""
    history = load_history()
    if not history:
        return {'history': [], 'best': None}
    best = None
    if CALIB_BEST.exists():
        try:
            with open(CALIB_BEST, encoding='utf-8') as f:
                best = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # 简化 iterations: 每次校准只保留前 5 + 最佳
    simplified = []
    for h in history:
        iters = h.get('iterations', [])
        if not iters:
            continue
        # 找 best iter
        best_iter_idx = min(range(len(iters)), key=lambda i: iters[i]['loss'])
        simplified.append({
            'timestamp': h.get('timestamp'),
            'n_iter': h.get('n_iter'),
            'method': h.get('method'),
            'base_loss': h.get('base_loss'),
            'best_loss': h.get('best_loss'),
            'best_iter': h.get('best_iter'),
            'improvement': h.get('improvement'),
            'iterations_summary': {
                'total': len(iters),
                'first_loss': iters[0]['loss'],
                'last_loss': iters[-1]['loss'],
                'min_loss': min(i['loss'] for i in iters),
                'losses': [i['loss'] for i in iters],  # 折线图用
            },
        })
    return {'history': simplified, 'best': best}


if __name__ == '__main__':
    # 评估当前默认
    from weights_schema import DEFAULT
    print("=== 评估当前默认 weights ===")
    ev = evaluate(DEFAULT)
    print()

    # 跑 5 轮校准 (scikit-optimize 不可用就 grid)
    if len(load_results()) >= 2:
        print("\n=== 启动校准 ===")
        result = calibrate(n_iter=10, use_bayes=True)
        if 'error' in result:
            print(f"  [err] {result['error']}")
    else:
        print(f"  [skip] match_results.csv 至少 2 场才能校准")
