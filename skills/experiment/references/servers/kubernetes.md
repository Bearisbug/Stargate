# Kubernetes 集群操作指南

> 参考：[Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/) | [Schedule GPUs](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)

## 提交训练 Job

```yaml
# job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: <job-name>
spec:
  backoffLimit: 2                  # 失败重试次数
  ttlSecondsAfterFinished: 3600   # 完成后自动清理
  template:
    spec:
      restartPolicy: Never         # Job 必须为 Never 或 OnFailure
      containers:
      - name: trainer
        image: <registry>/<image>:<tag>
        command: ["python", "train.py", "--output-dir", "/outputs"]
        resources:
          limits:
            nvidia.com/gpu: "1"    # GPU 只能在 limits 中指定，不能只写 requests
        volumeMounts:
        - name: data
          mountPath: /data
        - name: outputs
          mountPath: /outputs
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: <data-pvc>
      - name: outputs
        persistentVolumeClaim:
          claimName: <output-pvc>
```

```bash
kubectl apply -f job.yaml
```

**GPU 资源名称**因集群安装的 device plugin 不同：
- NVIDIA GPU：`nvidia.com/gpu`
- AMD GPU：`amd.com/gpu`
- 集群自定义：询问管理员

GPU **只能**写在 `limits` 中，不能只写 `requests`。

## 常用命令

```bash
# 查看 job 状态
kubectl get jobs
kubectl get pods -l job-name=<job-name>

# 实时查看日志
kubectl logs -f <pod-name>
kubectl logs jobs/<job-name>       # 直接用 job 名（单 Pod 时有效）

# 查看失败原因
kubectl describe pod <pod-name>

# 删除 job（会同时删除关联 Pod）
kubectl delete job <job-name>
```

## 拷贝结果

```bash
kubectl cp <pod-name>:/outputs/result.json ./result.json
```

## 查看 Pod 名

```bash
kubectl get pods -l job-name=<job-name> -o jsonpath='{.items[0].metadata.name}'
```

## 注意

- `restartPolicy` 必须是 `Never` 或 `OnFailure`，不能是 `Always`
- 镜像须提前 push 到集群可访问的 registry
- Job 完成后 Pod 默认保留，建议设置 `ttlSecondsAfterFinished` 自动清理
- 不同集群的 GPU resource name 不同，先 `kubectl describe node` 查看节点可用资源
