-- 1. Basic Work Orders with Product, Work Center, Machine, and Employee details
SELECT 
    wo.OrderID,
    p.Name AS ProductName,
    wo.Quantity,
    wo.Status,
    wo.PlannedStartTime,
    wo.PlannedEndTime,
    wc.Name AS WorkCenterName,
    m.Name AS MachineName,
    e.Name AS EmployeeName
FROM 
    WorkOrders wo
JOIN 
    Products p ON wo.ProductID = p.ProductID
JOIN 
    WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
JOIN 
    Machines m ON wo.MachineID = m.MachineID
JOIN 
    Employees e ON wo.EmployeeID = e.EmployeeID
ORDER BY 
    wo.PlannedStartTime DESC
LIMIT 20;

-- 2. Inventory levels with Supplier information and reorder alerts
SELECT 
    i.ItemID,
    i.Name AS ItemName,
    i.Category AS Category,
    i.Quantity,
    i.ReorderLevel,
    CASE 
        WHEN i.Quantity <= i.ReorderLevel THEN 'REORDER NEEDED'
        WHEN i.Quantity <= i.ReorderLevel * 1.25 THEN 'LOW STOCK'
        ELSE 'OK'
    END AS StockStatus,
    i.LeadTime AS LeadTimeDays,
    s.Name AS SupplierName,
    i.Location AS StorageLocation,
    i.LastReceivedDate
FROM 
    Inventory i
JOIN 
    Suppliers s ON i.SupplierID = s.SupplierID
ORDER BY 
    (CASE WHEN i.Quantity <= i.ReorderLevel THEN 0
          WHEN i.Quantity <= i.ReorderLevel * 1.25 THEN 1
          ELSE 2
     END),
    i.Name
LIMIT 30;

-- 3. Bill of Materials for a specific product with cost analysis
SELECT 
    p.Name AS ProductName,
    i.Name AS ComponentName,
    i.Category AS ComponentCategory,
    bom.Quantity AS QuantityRequired,
    bom.ScrapFactor AS ScrapFactor,
    i.Cost AS UnitCost,
    ROUND(bom.Quantity * i.Cost, 2) AS ComponentCost,
    ROUND(bom.Quantity * i.Cost * (1 + bom.ScrapFactor), 2) AS TotalCostWithScrap
FROM 
    BillOfMaterials bom
JOIN 
    Products p ON bom.ProductID = p.ProductID
JOIN 
    Inventory i ON bom.ComponentID = i.ItemID
WHERE 
    p.Name = 'eBike T101'
ORDER BY 
    ComponentCost DESC;

-- 4. Machine Efficiency, Maintenance Schedule, and OEE Analysis
SELECT 
    m.MachineID,
    m.Name AS MachineName,
    m.Type,
    m.Status,
    m.NominalCapacity,
    m.CapacityUOM,
    m.EfficiencyFactor,
    m.LastMaintenanceDate,
    m.NextMaintenanceDate,
    ROUND(JULIANDAY(m.NextMaintenanceDate) - JULIANDAY('now'), 1) AS DaysUntilMaintenance,
    oee.Availability,
    oee.Performance,
    oee.Quality,
    oee.OEE
FROM 
    Machines m
LEFT JOIN 
    (SELECT 
        MachineID, 
        AVG(Availability) AS Availability,
        AVG(Performance) AS Performance,
        AVG(Quality) AS Quality,
        AVG(OEE) AS OEE
     FROM 
        OEEMetrics
     WHERE 
        Date >= DATE('now', '-7 days')
     GROUP BY 
        MachineID) oee ON m.MachineID = oee.MachineID
ORDER BY 
    DaysUntilMaintenance
LIMIT 20;

-- 5. Quality Control results with detailed defect analysis
SELECT 
    qc.CheckID,
    wo.OrderID,
    p.Name AS ProductName,
    qc.Date,
    qc.Result,
    qc.DefectRate,
    qc.ReworkRate,
    qc.YieldRate,
    COUNT(d.DefectID) AS DefectCount,
    GROUP_CONCAT(d.DefectType || ' (' || d.Quantity || ')') AS DefectDetails,
    e.Name AS Inspector
FROM 
    QualityControl qc
JOIN 
    WorkOrders wo ON qc.OrderID = wo.OrderID
JOIN 
    Products p ON wo.ProductID = p.ProductID
JOIN 
    Employees e ON qc.InspectorID = e.EmployeeID
LEFT JOIN 
    Defects d ON qc.CheckID = d.CheckID
GROUP BY 
    qc.CheckID
ORDER BY 
    qc.Date DESC
LIMIT 20;

-- 6. Production Output and Schedule Adherence
SELECT 
    wo.OrderID,
    p.Name AS ProductName,
    wo.Quantity AS PlannedQuantity,
    wo.ActualProduction,
    wo.Scrap,
    CASE 
        WHEN wo.Status = 'completed' THEN 
            ROUND((wo.ActualProduction * 1.0 / wo.Quantity) * 100, 1) 
        ELSE NULL 
    END AS CompletionPercentage,
    wo.PlannedStartTime,
    wo.ActualStartTime,
    wo.PlannedEndTime,
    wo.ActualEndTime,
    ROUND((JULIANDAY(wo.ActualEndTime) - JULIANDAY(wo.ActualStartTime)) * 24, 2) AS ActualHours,
    ROUND((JULIANDAY(wo.PlannedEndTime) - JULIANDAY(wo.PlannedStartTime)) * 24, 2) AS PlannedHours,
    CASE 
        WHEN wo.Status = 'completed' AND wo.ActualEndTime > wo.PlannedEndTime THEN 'LATE'
        WHEN wo.Status = 'completed' AND wo.ActualEndTime <= wo.PlannedEndTime THEN 'ON TIME'
        ELSE wo.Status
    END AS ScheduleStatus
FROM 
    WorkOrders wo
JOIN 
    Products p ON wo.ProductID = p.ProductID
WHERE 
    wo.Status IN ('completed', 'in_progress')
ORDER BY 
    wo.ActualStartTime DESC
LIMIT 20;

-- 7. Machine Downtime Analysis
SELECT 
    m.Name AS MachineName,
    m.Type AS MachineType, 
    d.Category AS DowntimeCategory,
    d.Reason,
    COUNT(*) AS OccurrenceCount,
    SUM(d.Duration) AS TotalMinutes,
    ROUND(AVG(d.Duration), 1) AS AvgDurationMinutes,
    ROUND(SUM(d.Duration) * 100.0 / (SELECT SUM(Duration) FROM Downtimes), 2) AS PercentOfTotalDowntime
FROM 
    Downtimes d
JOIN 
    Machines m ON d.MachineID = m.MachineID
GROUP BY 
    m.Type, d.Reason
ORDER BY 
    TotalMinutes DESC
LIMIT 20;

-- 8. Material Consumption Analysis
SELECT 
    p.Name AS Product,
    i.Name AS Material,
    COUNT(DISTINCT mc.OrderID) AS OrderCount,
    SUM(mc.PlannedQuantity) AS TotalPlannedQty,
    SUM(mc.ActualQuantity) AS TotalActualQty,
    ROUND(AVG(mc.VariancePercent), 2) AS AvgVariancePercent,
    ROUND((SUM(mc.ActualQuantity) - SUM(mc.PlannedQuantity)) / SUM(mc.PlannedQuantity) * 100, 2) AS OverallVariancePercent,
    SUM(mc.ActualQuantity * i.Cost) AS TotalMaterialCost
FROM 
    MaterialConsumption mc
JOIN 
    WorkOrders wo ON mc.OrderID = wo.OrderID
JOIN 
    Products p ON wo.ProductID = p.ProductID
JOIN 
    Inventory i ON mc.ItemID = i.ItemID
WHERE 
    wo.Status = 'completed'
GROUP BY 
    p.ProductID, i.ItemID
ORDER BY 
    TotalMaterialCost DESC
LIMIT 20;

-- 9. OEE (Overall Equipment Effectiveness) Trend Analysis
SELECT 
    m.Name AS MachineName,
    strftime('%Y-%m-%d', oee.Date) AS Date,
    ROUND(oee.Availability * 100, 1) AS AvailabilityPercent,
    ROUND(oee.Performance * 100, 1) AS PerformancePercent,
    ROUND(oee.Quality * 100, 1) AS QualityPercent,
    ROUND(oee.OEE * 100, 1) AS OEEPercent,
    oee.PlannedProductionTime AS PlannedMinutes,
    oee.Downtime AS DowntimeMinutes
FROM 
    OEEMetrics oee
JOIN 
    Machines m ON oee.MachineID = m.MachineID
WHERE 
    oee.Date >= DATE('now', '-14 days')
ORDER BY 
    m.Name, oee.Date
LIMIT 30;

-- 10. Work Center Capacity Analysis
SELECT 
    wc.Name AS WorkCenter,
    wc.Capacity AS NominalCapacity,
    wc.CapacityUOM,
    COUNT(DISTINCT m.MachineID) AS MachineCount,
    SUM(m.NominalCapacity) AS TotalMachineCapacity,
    (SELECT COUNT(*) FROM WorkOrders wo WHERE wo.WorkCenterID = wc.WorkCenterID AND wo.Status IN ('scheduled', 'in_progress')) AS ActiveOrders,
    (SELECT SUM(wo.Quantity) FROM WorkOrders wo WHERE wo.WorkCenterID = wc.WorkCenterID AND wo.Status IN ('scheduled', 'in_progress')) AS TotalOrderedQuantity,
    wc.Location
FROM 
    WorkCenters wc
LEFT JOIN 
    Machines m ON wc.WorkCenterID = m.WorkCenterID
GROUP BY 
    wc.WorkCenterID
ORDER BY 
    ActiveOrders DESC;

-- 11. Employee Productivity Analysis
SELECT 
    e.Name AS Employee,
    e.Role,
    s.Name AS Shift,
    COUNT(wo.OrderID) AS CompletedOrders,
    SUM(wo.Quantity) AS TotalProduction,
    SUM(wo.ActualProduction) AS TotalGoodUnits,
    ROUND(SUM(wo.Scrap) * 100.0 / NULLIF(SUM(wo.Quantity), 0), 2) AS ScrapRate,
    ROUND(AVG(JULIANDAY(wo.ActualEndTime) - JULIANDAY(wo.ActualStartTime)) * 24, 1) AS AvgOrderHours,
    COUNT(DISTINCT wo.ProductID) AS ProductVariety
FROM 
    Employees e
JOIN 
    Shifts s ON e.ShiftID = s.ShiftID
LEFT JOIN 
    WorkOrders wo ON e.EmployeeID = wo.EmployeeID AND wo.Status = 'completed'
WHERE 
    e.Role = 'Operator'
GROUP BY 
    e.EmployeeID
ORDER BY 
    TotalGoodUnits DESC
LIMIT 15;

-- 12. Production Schedule for Next Week
SELECT 
    wo.OrderID,
    p.Name AS Product,
    wo.Quantity,
    wo.Priority,
    wo.PlannedStartTime,
    wo.PlannedEndTime,
    ROUND((JULIANDAY(wo.PlannedEndTime) - JULIANDAY(wo.PlannedStartTime)) * 24, 1) AS DurationHours,
    wc.Name AS WorkCenter,
    m.Name AS Machine,
    e.Name AS Operator
FROM 
    WorkOrders wo
JOIN 
    Products p ON wo.ProductID = p.ProductID
JOIN 
    WorkCenters wc ON wo.WorkCenterID = wc.WorkCenterID
JOIN 
    Machines m ON wo.MachineID = m.MachineID
JOIN 
    Employees e ON wo.EmployeeID = e.EmployeeID
WHERE 
    wo.Status = 'scheduled'
    AND wo.PlannedStartTime BETWEEN DATETIME('now') AND DATETIME('now', '+7 days')
ORDER BY 
    wo.Priority DESC, wo.PlannedStartTime
LIMIT 30;