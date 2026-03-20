import torch
import time
from tqdm import tqdm

def simulate_gpu_progress(total_simulations, num_buffs=18, buffs_per_bottle=3):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != 'cuda':
        print("😭 没找到显卡，无法开启极速模式！")
        return

    print(f"✅ 核心已就绪：{torch.cuda.get_device_name(0)}")
    
    # 设定每批次大小 (1000万次/批)
    batch_size = 10000000 
    num_batches = (total_simulations + batch_size - 1) // batch_size
    
    target_mask = (1 << num_buffs) - 1
    start_time = time.time()

    # 用于存放结果的列表
    all_results = []

    print(f"🚀 开始集齐 18 种增益的终极挑战...")

    # 使用 tqdm 创建进度条
    with tqdm(total=total_simulations, desc="模拟进度", unit="次") as pbar:
        remaining = total_simulations
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            
            # --- GPU 并行计算核心 ---
            # 初始化当前批次的状态
            finished = torch.zeros(current_batch, dtype=torch.bool, device=device)
            bottles_drunk = torch.zeros(current_batch, dtype=torch.int32, device=device)
            current_masks = torch.zeros(current_batch, dtype=torch.int32, device=device)

            # 循环直到本批次所有模拟都达成全增益
            while not torch.all(finished):
                # 仅对未完成的模拟增加瓶数
                bottles_drunk[~finished] += 1
                
                # 模拟每瓶提供的 3 个随机增益
                for _ in range(buffs_per_bottle):
                    # 批量生成随机索引 [0, 17]
                    random_indices = torch.randint(0, num_buffs, (current_batch,), device=device)
                    # 位运算更新掩码
                    new_bits = torch.pow(2, random_indices).to(torch.int32)
                    current_masks |= new_bits
                
                # 更新完成状态
                finished = (current_masks == target_mask)

            # 将本批次结果移回 CPU 并清空显存缓存
            all_results.append(bottles_drunk.cpu())
            
            # 更新进度条
            pbar.update(current_batch)
            remaining -= current_batch
            
            # 释放不再需要的显存空间
            torch.cuda.empty_cache()

    # 汇总并统计
    final_results = torch.cat(all_results).numpy()
    final_results.sort()
    
    end_time = time.time()

    print("\n📊 --- 21 亿次模拟实验报告 ---")
    print(f"⏱️  总耗时：{end_time - start_time:.2f} 秒")
    print(f"🔹 平均需要：{final_results.mean():.4f} 瓶")
    print(f"🔹 50% 的人集齐需要：{final_results[int(total_simulations * 0.5)]} 瓶")
    print(f"🔹 95% 的人集齐需要：{final_results[int(total_simulations * 0.95)]} 瓶")
    print(f"🍀 全球最强欧皇：{final_results[0]} 瓶")
    print(f"💀 全球最惨非酋：{final_results[-1]} 瓶")
    print(f"\n(づ｡◕‿‿◕｡)づ 主人的 4060 Ti 真是太可靠啦！")

if __name__ == "__main__":
    try:
        val = input("请输入模拟总次数 (建议 1 亿以上来测试显卡): ")
        count = int(val) if val.strip() else 1000000
        simulate_gpu_progress(count)
    except Exception as e:
        print(f"哎呀，程序撒娇了：{e}")