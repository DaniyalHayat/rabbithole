# Independent base-R replication of the Python graph authority calculation.
# Run from repository root: Rscript replication/pagerank.R
r <- read.csv('outputs/pagerank_reference.csv', stringsAsFactors=FALSE)
e <- read.csv('outputs/citation_edges.csv', stringsAsFactors=FALSE)
n <- nrow(r); src <- match(e$source,r$id); dst <- match(e$target,r$id)
stopifnot(!anyNA(src),!anyNA(dst))
degree <- tabulate(src,nbins=n); rank <- rep(1/n,n)
for(iter in 1:300) {
  next_rank <- rep((1-.85)/n + .85*sum(rank[degree==0])/n,n)
  mass <- rowsum(.85*rank[src]/degree[src],dst,reorder=FALSE)
  next_rank[as.integer(rownames(mass))] <- next_rank[as.integer(rownames(mass))] + mass[,1]
  if(sum(abs(next_rank-rank))<1e-11) {rank<-next_rank;break}
  rank<-next_rank
}
rank<-rank/sum(rank)
stopifnot(max(abs(rank-r$pagerank))<1e-9)
write.csv(data.frame(id=r$id,pagerank=rank),'outputs/r_pagerank.csv',row.names=FALSE)
m<-read.csv('outputs/query_metrics.csv')
set.seed(42)
boot<-replicate(5000,mean(sample(m$difference,replace=TRUE)))
print(c(mean_difference=mean(m$difference),quantile(boot,c(.025,.975))))
ci<-quantile(boot,c(.025,.975))
summary<-data.frame(comparison='hybrid_minus_bm25',mean_difference=mean(m$difference),lower=ci[1],upper=ci[2])
if(file.exists('outputs/ml_query_metrics.csv')) {
  ml<-read.csv('outputs/ml_query_metrics.csv');set.seed(42)
  mlboot<-replicate(5000,mean(sample(ml$difference,replace=TRUE)))
  ci<-quantile(mlboot,c(.025,.975))
  summary<-rbind(summary,data.frame(comparison='ml_minus_hybrid',mean_difference=mean(ml$difference),lower=ci[1],upper=ci[2]))
}
write.csv(summary,'outputs/r_metric_summary.csv',row.names=FALSE)
cat('PageRank parity passed; bootstrap RNG differs from NumPy.\n')
