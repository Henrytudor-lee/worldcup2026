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

    return {
        'match_count': matched,
        'win_correct': win_correct,
        'win_accuracy': round(accuracy, 4),
        'score_mae': round(mae, 3),
        'score_correct': score_correct,
        'loss': round(loss, 3),
        'details': details,
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
        """params 列表 → weights dict"""
        w = deepcopy(DEFAULT)
        for i, name in enumerate(param_names):
            v = params[i]
            if '.' in name:
                g, k = name.split('.', 1)
                # int 字段 (position_top_n.*) 要 round
                if (g, k) in INT_FIELDS:
                    w[g][k] = max(1, int(round(v)))
                else:
                    w[g][k] = v
            else:
                w[name] = v
        return w

    def eval_loss(params):
        w = params_to_weights(params)
        ok, _ = validate(w)
        if not ok:
            return 100  # 极端值返回大 loss
        # 防 0 除: smoothing 分母不能 = 0
        for k in ('player_div', 'coach_div', 'rank_div'):
            if w['smoothing'].get(k, 0) < 1:
                return 100
        try:
            ev = evaluate(w, verbose=False)
            if 'error' in ev:
                return 100
            return ev['loss']
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
            result = gp_minimize(
                eval_loss,
                space,
                n_calls=n_iter,
                n_initial_points=min(10, n_iter // 2),
                random_state=42,
                verbose=False,
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
        for i in range(n_random):
            combo = [random.uniform(lo, hi) for lo, hi in space]
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
            if loss < best_loss:
                best_loss = loss
                best_weights = w
                best_iter = i
            # 实时日志
            log('iter', f"iter {i+1}/{n_random}: loss={loss:.2f} acc={ev.get('win_accuracy',0):.0%} mae={ev.get('score_mae',0):.2f} {'🏆 NEW BEST' if loss == best_loss else ''}")

    # 4. 保存历史
    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'n_iter': n_iter,
        'method': 'bayes' if use_bayes else 'grid',
        'base_loss': base_eval['loss'],
        'best_loss': best_loss,
        'best_iter': best_iter,
        'improvement': round(base_eval['loss'] - best_loss, 3),
        'best_weights': best_weights,
        'iterations': all_iterations,
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
    log('done', f"  history_count: {len(history)}, best_weights 已存盘")

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
