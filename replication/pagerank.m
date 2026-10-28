% MATLAB independent sparse-matrix PageRank. Run from repository root.
projectRoot=fileparts(fileparts(mfilename('fullpath'))); cd(projectRoot);
r=readtable('outputs/pagerank_reference.csv','TextType','string');
e=readtable('outputs/citation_edges.csv','TextType','string');
[ok1,src]=ismember(e.source,r.id); [ok2,dst]=ismember(e.target,r.id);
assert(all(ok1)&all(ok2)); n=height(r); degree=accumarray(src,1,[n 1]);
P=sparse(dst,src,1./degree(src),n,n); rank=ones(n,1)/n;
for iter=1:300
    nextRank=(1-.85)*ones(n,1)/n+.85*(P*rank+sum(rank(degree==0))/n);
    if sum(abs(nextRank-rank))<1e-11
        rank=nextRank; break
    end
    rank=nextRank;
end
rank=rank/sum(rank); assert(max(abs(rank-r.pagerank))<1e-9);
writetable(table(r.id,rank,'VariableNames',{'id','pagerank'}),'outputs/matlab_pagerank.csv');
disp('MATLAB PageRank parity passed');
% Base-MATLAB paired bootstrap; no Statistics Toolbox required.
comparisons=["hybrid_minus_bm25";"ml_minus_hybrid"];
files=["outputs/query_metrics.csv";"outputs/ml_query_metrics.csv"];
point=zeros(2,1); lower=zeros(2,1); upper=zeros(2,1);
for k=1:2
    m=readtable(files(k)); difference=m.difference; n=height(m); rng(42);
    boot=zeros(5000,1);
    for j=1:5000
        boot(j)=mean(difference(randi(n,n,1)));
    end
    ordered=sort(boot); point(k)=mean(difference);
    lower(k)=ordered(ceil(.025*5000)); upper(k)=ordered(ceil(.975*5000));
end
writetable(table(comparisons,point,lower,upper),'outputs/matlab_metric_summary.csv');
disp('MATLAB paired-metric replication complete');
