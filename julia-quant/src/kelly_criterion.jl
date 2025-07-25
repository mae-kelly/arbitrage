using Distributions
using Optimization

struct KellyCriterion
   win_probability::Float64
   avg_win::Float64
   avg_loss::Float64
   max_fraction::Float64
end

function optimal_fraction(kelly::KellyCriterion)
   f_star = (kelly.win_probability * kelly.avg_win - (1 - kelly.win_probability) * kelly.avg_loss) / 
            (kelly.avg_win * kelly.avg_loss)
   
   return min(f_star, kelly.max_fraction)
end

function kelly_fraction_continuous(returns::Vector{Float64}, max_fraction::Float64=0.25)
   μ = mean(returns)
   σ² = var(returns)
   
   if σ² == 0
       return 0.0
   end
   
   f_star = μ / σ²
   return min(max(f_star, 0.0), max_fraction)
end

function dynamic_kelly_sizing(historical_returns::Vector{Float64}, 
                           lookback_window::Int=100,
                           max_fraction::Float64=0.02)
   
   if length(historical_returns) < lookback_window
       return kelly_fraction_continuous(historical_returns, max_fraction)
   end
   
   recent_returns = historical_returns[end-lookback_window+1:end]
   return kelly_fraction_continuous(recent_returns, max_fraction)
end

function multi_asset_kelly(expected_returns::Vector{Float64}, 
                         covariance_matrix::Matrix{Float64},
                         max_total_fraction::Float64=0.1)
   
   inv_cov = inv(covariance_matrix)
   optimal_fractions = inv_cov * expected_returns
   
   total_fraction = sum(abs.(optimal_fractions))
   if total_fraction > max_total_fraction
       optimal_fractions *= max_total_fraction / total_fraction
   end
   
   return max.(optimal_fractions, 0.0)
end
