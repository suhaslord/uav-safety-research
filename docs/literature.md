# Literature Map

This project is motivated by research showing that autonomous systems benefit from explicitly connecting perception uncertainty to downstream decisions.

## Starting references

1. Arnez, F., Radermacher, A., & Espinoza, H. **Quantifying and Using System Uncertainty in UAV Navigation.** arXiv:2206.01953 (2022).  
   https://arxiv.org/abs/2206.01953

2. Dong, H. **Vision-based control for landing an aerial vehicle on a marine vessel.** arXiv:2404.11336 (2024).  
   https://arxiv.org/abs/2404.11336

3. de la Torre-Vanegas, J., Soriano-Garcia, M., Becerra, I., & Mercado-Ravell, D. **Vision-Based Risk Aware Emergency Landing for UAVs in Complex Urban Environments.** arXiv:2505.20423 (2025).  
   https://arxiv.org/abs/2505.20423

4. Chen, L., Yuan, X., Xiao, Y., Zhang, Y., & Zhu, J. **Robust Autonomous Landing of UAV in Non-Cooperative Environments based on Dynamic Time Camera-LiDAR Fusion.** arXiv:2011.13761 (2020).  
   https://arxiv.org/abs/2011.13761

## What this student project adds

AegisLand does **not** attempt to reproduce those full systems. Instead, it creates a small, transparent experiment around one question:

> If visual perception becomes unreliable during landing, how much safety can be gained by making uncertainty an explicit input to the decision layer?

The first phase is deliberately simple enough to inspect, reproduce, and criticize. Later phases can replace the surrogate perception model with image-based estimation.
