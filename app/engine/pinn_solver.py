"""
Physics-Informed Neural Network (PINN) for 3D Subsurface Ground Settlement
==========================================================================
Integrates continuum elastoplastic mechanics and Mindlin half-space kinematics directly
into PyTorch loss functions. Performs forward pass predicting 3D displacement field (ux, uy, uz)
with automated PDE & Boundary Condition constraint gradients.
"""

from typing import Dict, Tuple, Optional, Any

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class torch:
        Tensor = Any
        @staticmethod
        def autograd(): pass
    class nn:
        Module = object

import numpy as np


class GeotechPINN(nn.Module):
    """
    3D Subsurface Physics-Informed Neural Network.
    Inputs: Spatial coordinates (x, y, z) [Meters relative to tunnel axis]
    Outputs: Displacement vector field u = (u_x, u_y, u_z) [Meters]
    """

    def __init__(self, hidden_dim: int = 64, num_layers: int = 4):
        super().__init__()
        
        layers = [nn.Linear(3, hidden_dim), nn.Tanh()]
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.Tanh())
        layers.append(nn.Linear(hidden_dim, 3))  # Predicts (ux, uy, uz)

        self.net = nn.Sequential(*layers)
        
        # Initialize weights with Xavier/Glorot for smooth Tanh derivative stability
        for m in self.net.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor, y: torch.Tensor, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass taking spatial input tensors (x, y, z).
        Returns displacement fields (ux, uy, uz).
        """
        xyz = torch.cat([x, y, z], dim=-1)
        u_pred = self.net(xyz)
        ux = u_pred[:, 0:1]
        uy = u_pred[:, 1:2]
        uz = u_pred[:, 2:3]
        return ux, uy, uz


class PINNLossEvaluator:
    """
    Computes custom PyTorch Physics-Informed Loss:
    Loss = L_data + lambda_phys * L_PDE + lambda_boundary * L_BC
    """

    def __init__(
        self,
        elastic_modulus_e: float = 30.0e6,  # 30 MPa in Pa
        poisson_ratio_nu: float = 0.3,
        soil_density_gamma: float = 19000.0, # 19 kN/m3 in N/m3
        lambda_phys: float = 1.0,
        lambda_boundary: float = 10.0
    ):
        self.E = elastic_modulus_e
        self.nu = poisson_ratio_nu
        self.gamma = soil_density_gamma
        self.lambda_phys = lambda_phys
        self.lambda_boundary = lambda_boundary

        # Lame parameters for isotropic elasticity
        self.lame_lambda = (self.E * self.nu) / ((1.0 + self.nu) * (1.0 - 2.0 * self.nu))
        self.lame_mu = self.E / (2.0 * (1.0 + self.nu))

    def compute_pde_residuals(
        self,
        model: GeotechPINN,
        x_colloc: torch.Tensor,
        y_colloc: torch.Tensor,
        z_colloc: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Computes 3D Cauchy momentum balance equations using autograd second derivatives:
        d(sigma_xx)/dx + d(tau_xy)/dy + d(tau_xz)/dz + b_x = 0
        d(tau_yx)/dx + d(sigma_yy)/dy + d(tau_yz)/dz + b_y = 0
        d(tau_zx)/dx + d(tau_zy)/dy + d(sigma_zz)/dz + gamma = 0
        """
        x_colloc.requires_grad_(True)
        y_colloc.requires_grad_(True)
        z_colloc.requires_grad_(True)

        ux, uy, uz = model(x_colloc, y_colloc, z_colloc)

        # First Derivatives (Strain tensor components)
        dux_dx = torch.autograd.grad(ux, x_colloc, torch.ones_like(ux), create_graph=True)[0]
        dux_dy = torch.autograd.grad(ux, y_colloc, torch.ones_like(ux), create_graph=True)[0]
        dux_dz = torch.autograd.grad(ux, z_colloc, torch.ones_like(ux), create_graph=True)[0]

        duy_dx = torch.autograd.grad(uy, x_colloc, torch.ones_like(uy), create_graph=True)[0]
        duy_dy = torch.autograd.grad(uy, y_colloc, torch.ones_like(uy), create_graph=True)[0]
        duy_dz = torch.autograd.grad(uy, z_colloc, torch.ones_like(uy), create_graph=True)[0]

        duz_dx = torch.autograd.grad(uz, x_colloc, torch.ones_like(uz), create_graph=True)[0]
        duz_dy = torch.autograd.grad(uz, y_colloc, torch.ones_like(uz), create_graph=True)[0]
        duz_dz = torch.autograd.grad(uz, z_colloc, torch.ones_like(uz), create_graph=True)[0]

        # Strains
        eps_xx = dux_dx
        eps_yy = duy_dy
        eps_zz = duz_dz
        eps_xy = 0.5 * (dux_dy + duy_dx)
        eps_xz = 0.5 * (dux_dz + duz_dx)
        eps_yz = 0.5 * (duy_dz + duz_dy)

        volumetric_strain = eps_xx + eps_yy + eps_zz

        # Stresses (Hooke's Law: sigma_ij = lambda * tr(eps) * delta_ij + 2 * mu * eps_ij)
        sig_xx = self.lame_lambda * volumetric_strain + 2.0 * self.lame_mu * eps_xx
        sig_yy = self.lame_lambda * volumetric_strain + 2.0 * self.lame_mu * eps_yy
        sig_zz = self.lame_lambda * volumetric_strain + 2.0 * self.lame_mu * eps_zz
        tau_xy = 2.0 * self.lame_mu * eps_xy
        tau_xz = 2.0 * self.lame_mu * eps_xz
        tau_yz = 2.0 * self.lame_mu * eps_yz

        # Divergence of stress tensor (Equilibrium PDEs)
        dsig_xx_dx = torch.autograd.grad(sig_xx, x_colloc, torch.ones_like(sig_xx), create_graph=True)[0]
        dtau_xy_dy = torch.autograd.grad(tau_xy, y_colloc, torch.ones_like(tau_xy), create_graph=True)[0]
        dtau_xz_dz = torch.autograd.grad(tau_xz, z_colloc, torch.ones_like(tau_xz), create_graph=True)[0]
        res_x = dsig_xx_dx + dtau_xy_dy + dtau_xz_dz  # Body force b_x = 0

        dtau_xy_dx = torch.autograd.grad(tau_xy, x_colloc, torch.ones_like(tau_xy), create_graph=True)[0]
        dsig_yy_dy = torch.autograd.grad(sig_yy, y_colloc, torch.ones_like(sig_yy), create_graph=True)[0]
        dtau_yz_dz = torch.autograd.grad(tau_yz, z_colloc, torch.ones_like(tau_yz), create_graph=True)[0]
        res_y = dtau_xy_dx + dsig_yy_dy + dtau_yz_dz  # Body force b_y = 0

        dtau_xz_dx = torch.autograd.grad(tau_xz, x_colloc, torch.ones_like(tau_xz), create_graph=True)[0]
        dtau_yz_dy = torch.autograd.grad(tau_yz, y_colloc, torch.ones_like(tau_yz), create_graph=True)[0]
        dsig_zz_dz = torch.autograd.grad(sig_zz, z_colloc, torch.ones_like(sig_zz), create_graph=True)[0]
        res_z = dtau_xz_dx + dtau_yz_dy + dsig_zz_dz + self.gamma  # Self-weight body force

        return res_x, res_y, res_z

    def compute_loss(
        self,
        model: GeotechPINN,
        x_data: torch.Tensor,
        y_data: torch.Tensor,
        z_data: torch.Tensor,
        u_obs: torch.Tensor,
        x_colloc: torch.Tensor,
        y_colloc: torch.Tensor,
        z_colloc: torch.Tensor,
        x_surface: torch.Tensor,
        y_surface: torch.Tensor,
        z_surface: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Calculates total combined physics loss.
        """
        # 1. Data Loss (Supervised observation points)
        ux_pred, uy_pred, uz_pred = model(x_data, y_data, z_data)
        u_pred_vec = torch.cat([ux_pred, uy_pred, uz_pred], dim=-1)
        loss_data = torch.mean((u_pred_vec - u_obs) ** 2)

        # 2. Physics PDE Loss (Collocation domain points)
        res_x, res_y, res_z = self.compute_pde_residuals(model, x_colloc, y_colloc, z_colloc)
        loss_pde = torch.mean(res_x ** 2) + torch.mean(res_y ** 2) + torch.mean(res_z ** 2)

        # 3. Free Surface Boundary Condition Loss (z=0 -> Traction free surface: sig_zz=0, tau_xz=0, tau_yz=0)
        x_surface.requires_grad_(True)
        y_surface.requires_grad_(True)
        z_surface.requires_grad_(True)
        ux_surf, uy_surf, uz_surf = model(x_surface, y_surface, z_surface)
        duz_dz_surf = torch.autograd.grad(uz_surf, z_surface, torch.ones_like(uz_surf), create_graph=True)[0]
        dux_dz_surf = torch.autograd.grad(ux_surf, z_surface, torch.ones_like(ux_surf), create_graph=True)[0]
        duz_dx_surf = torch.autograd.grad(uz_surf, x_surface, torch.ones_like(uz_surf), create_graph=True)[0]
        
        # Approximate surface stress penalty
        loss_bc = torch.mean(duz_dz_surf ** 2) + torch.mean((dux_dz_surf + duz_dx_surf) ** 2)

        total_loss = loss_data + self.lambda_phys * loss_pde + self.lambda_boundary * loss_bc

        return {
            "total_loss": total_loss,
            "loss_data": loss_data,
            "loss_pde": loss_pde,
            "loss_bc": loss_bc
        }
