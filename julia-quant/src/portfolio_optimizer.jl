using JuMP, HiGHS
using LinearAlgebra
using Statistics

struct PortfolioOptimizer
   assets::Vector{String}
   expected_returns::Vector{Float64}
   covariance_matrix::Matrix{Float64}
   risk_aversion::Float64
end

function optimize_portfolio(optimizer::PortfolioOptimizer, 
                         max_position_sizes::Vector{Float64},
                         min_expected_return::Float64)
   
   n_assets = length(optimizer.assets)
   
   model = Model(HiGHS.Optimizer)
   set_silent(model)
   
   @variable(model, 0 <= weights[1:n_assets] <= 1)
   
   for i in 1:n_assets
       @constraint(model, weights[i] <= max_position_sizes[i])
   end
   
   @constraint(model, sum(weights) == 1)
   @constraint(model, dot(optimizer.expected_returns, weights) >= min_expected_return)
   
   portfolio_variance = weights' * optimizer.covariance_matrix * weights
   expected_return = dot(optimizer.expected_returns, weights)
   
   @objective(model, Max, expected_return - optimizer.risk_aversion * portfolio_variance)
   
   optimize!(model)
   
   if termination_status(model) == MOI.OPTIMAL
       optimal_weights = value.(weights)
       optimal_return = dot(optimizer.expected_returns, optimal_weights)
       optimal_risk = sqrt(optimal_weights' * optimizer.covariance_matrix * optimal_weights)
       
       return Dict(
           "weights" => optimal_weights,
           "expected_return" => optimal_return,
           "risk" => optimal_risk,
           "sharpe_ratio" => optimal_return / optimal_risk
       )
   else
       error("Optimization failed")
   end
end

function calculate_efficient_frontier(optimizer::PortfolioOptimizer, 
                                   max_position_sizes::Vector{Float64},
                                   n_points::Int=50)
   
   min_return = minimum(optimizer.expected_returns)
   max_return = maximum(optimizer.expected_returns)
   return_range = range(min_return, max_return, length=n_points)
   
   frontier_points = []
   
   for target_return in return_range
       try
           result = optimize_portfolio(optimizer, max_position_sizes, target_return)
           push!(frontier_points, (result["risk"], result["expected_return"]))
       catch
           continue
       end
   end
   
   return frontier_points
end
