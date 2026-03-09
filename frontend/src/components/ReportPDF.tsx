import React from 'react';
import { Document, Page, Text, View, StyleSheet, Font } from '@react-pdf/renderer';

// Register standard fonts if needed, but we'll use Helvetica for maximum reliability initially
// Colors from the Fintech Palette
const NAVY_BLUE = '#0B3C5D';
const SLATE_TEXT = '#334155';
const SLATE_LIGHT = '#94A3B8';
const EMERALD_GREEN = '#166534';
const ROSE_RED = '#991B1B';
const BG_SLATE_50 = '#F8FAFC';
const BORDER_COLOR = '#E2E2E2';

const styles = StyleSheet.create({
    page: {
        padding: 50,
        backgroundColor: '#FFFFFF',
        fontFamily: 'Helvetica',
        color: SLATE_TEXT,
    },
    // Header
    headerContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: 1,
        borderColor: BORDER_COLOR,
        paddingBottom: 15,
        marginBottom: 25,
    },
    logoBox: {
        width: 40,
        height: 40,
        backgroundColor: NAVY_BLUE,
        borderRadius: 4,
        justifyContent: 'center',
        alignItems: 'center',
    },
    logoText: {
        color: '#FFFFFF',
        fontWeight: 'bold',
        fontSize: 16,
    },
    headerBrandContainer: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    brandName: {
        fontSize: 18,
        fontWeight: 'bold',
        color: NAVY_BLUE,
        marginLeft: 10,
    },
    headerMetadata: {
        textAlign: 'right',
    },
    headerTitle: {
        fontSize: 10,
        fontWeight: 'bold',
        color: NAVY_BLUE,
    },
    headerSub: {
        fontSize: 8,
        color: SLATE_LIGHT,
        marginTop: 2,
    },
    // Sectioning
    section: {
        marginBottom: 20,
    },
    sectionHeading: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: BG_SLATE_50,
        padding: '6 10',
        marginBottom: 10,
        borderLeft: 3,
        borderColor: NAVY_BLUE,
    },
    sectionTitle: {
        fontSize: 12,
        fontWeight: 'bold',
        color: NAVY_BLUE,
        textTransform: 'uppercase',
        letterSpacing: 1,
    },
    bodyText: {
        fontSize: 10,
        lineHeight: 1.5,
        color: SLATE_TEXT,
        textAlign: 'justify',
    },
    // Scorecard
    scorecard: {
        flexDirection: 'row',
        backgroundColor: NAVY_BLUE,
        borderRadius: 8,
        padding: 20,
        marginBottom: 25,
        color: '#FFFFFF',
    },
    scoreItem: {
        flex: 1,
        alignItems: 'center',
    },
    scoreValue: {
        fontSize: 28,
        fontWeight: 'bold',
    },
    scoreLabel: {
        fontSize: 8,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginTop: 4,
        opacity: 0.8,
    },
    scoreGrade: {
        fontSize: 24,
        fontWeight: 'bold',
    },
    // Tables
    table: {
        marginTop: 10,
        borderWidth: 1,
        borderColor: BORDER_COLOR,
        borderRadius: 4,
        overflow: 'hidden',
    },
    tableHeader: {
        flexDirection: 'row',
        backgroundColor: NAVY_BLUE,
        color: '#FFFFFF',
        padding: '6 10',
    },
    tableRow: {
        flexDirection: 'row',
        borderBottomWidth: 1,
        borderColor: BORDER_COLOR,
        padding: '6 10',
    },
    cellLabel: {
        flex: 1,
        fontSize: 9,
        fontWeight: 'bold',
    },
    cellValue: {
        flex: 1,
        fontSize: 9,
        textAlign: 'right',
        fontFamily: 'Helvetica-Bold',
    },
    // List Items
    listItem: {
        flexDirection: 'row',
        marginBottom: 4,
        paddingLeft: 10,
    },
    listBullet: {
        width: 10,
        fontSize: 10,
        color: NAVY_BLUE,
    },
    listText: {
        flex: 1,
        fontSize: 9,
        lineHeight: 1.4,
    },
    // Footer
    footer: {
        position: 'absolute',
        bottom: 30,
        left: 50,
        right: 50,
        borderTop: 1,
        borderColor: BORDER_COLOR,
        paddingTop: 10,
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    footerText: {
        fontSize: 7,
        color: SLATE_LIGHT,
    },
    // Recommendation Block
    recommendationBlock: {
        borderWidth: 1,
        borderRadius: 6,
        padding: 15,
        marginTop: 10,
    },
    recTitle: {
        fontSize: 14,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    recExplanation: {
        fontSize: 10,
        lineHeight: 1.5,
        fontStyle: 'italic',
    }
});

interface ReportPDFProps {
    data: any;
}

const formatCurrency = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "N/A";
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(val);
};

const cleanText = (text: string) => {
    if (!text) return "";
    return text.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1').trim();
};

export const ReportPDF: React.FC<ReportPDFProps> = ({ data }) => {
    const report = data.report || data;
    const {
        company_name, sector, risk_analysis, financial_metrics,
        research_signals, recommendation, company_overview, financial_analysis,
        risk_assessment, industry_outlook, promoter_background
    } = report;

    const score = risk_analysis?.risk_score || 0;
    const grade = risk_analysis?.risk_grade || "N/A";
    const riskLevel = risk_analysis?.risk_level || "Medium";

    const metrics = [
        { label: "Annual Revenue", val: financial_metrics?.revenue },
        { label: "Net Profit (PAT)", val: financial_metrics?.profit },
        { label: "Aggregate Debt", val: financial_metrics?.debt },
        { label: "Bank Borrowings", val: financial_metrics?.bank_loans },
        { label: "Current Ratio", val: financial_metrics?.current_ratio },
        { label: "Debt to Equity Ratio", val: financial_metrics?.debt_to_equity_ratio },
    ];

    return (
        <Document>
            <Page size="A4" style={styles.page}>
                {/* Header */}
                <View style={styles.headerContainer} fixed>
                    <View style={styles.headerBrandContainer}>
                        <View style={styles.logoBox}>
                            <Text style={styles.logoText}>IC</Text>
                        </View>
                        <Text style={styles.brandName}>INTELLI-CREDIT</Text>
                    </View>
                    <View style={styles.headerMetadata}>
                        <Text style={styles.headerTitle}>APPRAISAL MEMORANDUM</Text>
                        <Text style={styles.headerSub}>ID: {data.analysis_id || 'N/A'}</Text>
                        <Text style={styles.headerSub}>GEN: {new Date().toLocaleDateString()}</Text>
                    </View>
                </View>

                {/* Cover Info */}
                <View style={{ marginBottom: 30 }}>
                    <Text style={{ fontSize: 28, fontWeight: 'bold', color: NAVY_BLUE }}>{company_name}</Text>
                    <Text style={{ fontSize: 12, color: SLATE_LIGHT, marginTop: 4 }}>SECTOR: {sector?.toUpperCase() || 'N/A'}</Text>
                </View>

                {/* Scorecard */}
                <View style={styles.scorecard}>
                    <View style={styles.scoreItem}>
                        <Text style={styles.scoreValue}>{score}</Text>
                        <Text style={styles.scoreLabel}>Risk Score</Text>
                    </View>
                    <View style={[styles.scoreItem, { borderLeft: 1, borderRight: 1, borderColor: 'rgba(255,255,255,0.2)' }]}>
                        <Text style={styles.scoreGrade}>{grade}</Text>
                        <Text style={styles.scoreLabel}>Credit Grade</Text>
                    </View>
                    <View style={styles.scoreItem}>
                        <Text style={[styles.scoreGrade, { fontSize: 16 }]}>{riskLevel.toUpperCase()}</Text>
                        <Text style={styles.scoreLabel}>Risk Level</Text>
                    </View>
                </View>

                {/* 1. Executive Summary */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>1. Executive Summary</Text>
                    </View>
                    <Text style={styles.bodyText}>{cleanText(report.executive_summary || "No summary provided.")}</Text>
                </View>

                {/* 2. Institutional Overview */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>2. Institutional Overview</Text>
                    </View>
                    <Text style={styles.bodyText}>{cleanText(company_overview || "N/A")}</Text>
                </View>

                {/* 3. Promoter Integrity */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>3. Promoter Background</Text>
                    </View>
                    <Text style={styles.bodyText}>{cleanText(promoter_background || "N/A")}</Text>
                </View>

                {/* Footer */}
                <View style={styles.footer} fixed>
                    <Text style={styles.footerText}>INTELLI-CREDIT CONFIDENTIAL | GEN-ID: {data.analysis_id || 'N/A'}</Text>
                    <Text style={styles.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                {/* 4. Financial Performance */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>4. Financial Performance</Text>
                    </View>
                    <Text style={styles.bodyText}>{cleanText(financial_analysis || "N/A")}</Text>

                    <View style={styles.table}>
                        <View style={styles.tableHeader}>
                            <Text style={[styles.cellLabel, { color: '#FFF' }]}>FINANCIAL METRIC</Text>
                            <Text style={[styles.cellValue, { color: '#FFF' }]}>VALUE (INR)</Text>
                        </View>
                        {metrics.map((m, i) => (
                            <View key={i} style={styles.tableRow}>
                                <Text style={styles.cellLabel}>{m.label}</Text>
                                <Text style={styles.cellValue}>
                                    {typeof m.val === 'number' && m.val > 1000 ? formatCurrency(m.val) : m.val?.toString() || "N/A"}
                                </Text>
                            </View>
                        ))}
                    </View>
                </View>

                {/* 5. Industry Outlook */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>5. Industry Outlook</Text>
                    </View>
                    <Text style={styles.bodyText}>{cleanText(industry_outlook || "N/A")}</Text>
                </View>

                {/* 6. Risk Assessment */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>6. Risk & Mitigation</Text>
                    </View>
                    {risk_analysis?.key_risks?.length > 0 && (
                        <View style={{ marginBottom: 10 }}>
                            <Text style={[styles.sectionTitle, { fontSize: 10, color: ROSE_RED, marginBottom: 5 }]}>Primary Risks:</Text>
                            {risk_analysis.key_risks.map((r: string, i: number) => (
                                <View key={i} style={styles.listItem}>
                                    <Text style={styles.listBullet}>-</Text>
                                    <Text style={styles.listText}>{cleanText(r)}</Text>
                                </View>
                            ))}
                        </View>
                    )}
                    {risk_analysis?.strengths?.length > 0 && (
                        <View>
                            <Text style={[styles.sectionTitle, { fontSize: 10, color: EMERALD_GREEN, marginBottom: 5 }]}>Strengths:</Text>
                            {risk_analysis.strengths.map((s: string, i: number) => (
                                <View key={i} style={styles.listItem}>
                                    <Text style={[styles.listBullet, { color: EMERALD_GREEN }]}>✓</Text>
                                    <Text style={styles.listText}>{cleanText(s)}</Text>
                                </View>
                            ))}
                        </View>
                    )}
                </View>

                {/* Footer */}
                <View style={styles.footer} fixed>
                    <Text style={styles.footerText}>INTELLI-CREDIT CONFIDENTIAL | GEN-ID: {data.analysis_id || 'N/A'}</Text>
                    <Text style={styles.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
                </View>
            </Page>

            <Page size="A4" style={styles.page}>
                {/* 7. Final Recommendation */}
                <View style={styles.section}>
                    <View style={styles.sectionHeading}>
                        <Text style={styles.sectionTitle}>7. Final Recommendation</Text>
                    </View>

                    <View style={[styles.recommendationBlock, {
                        borderColor: recommendation?.decision === 'APPROVE' ? EMERALD_GREEN : recommendation?.decision === 'REJECT' ? ROSE_RED : NAVY_BLUE,
                        backgroundColor: recommendation?.decision === 'APPROVE' ? '#F0FDF4' : recommendation?.decision === 'REJECT' ? '#FEF2F2' : '#F0F9FF'
                    }]}>
                        <Text style={[styles.recTitle, {
                            color: recommendation?.decision === 'APPROVE' ? EMERALD_GREEN : recommendation?.decision === 'REJECT' ? ROSE_RED : NAVY_BLUE
                        }]}>
                            DETERMINATION: {recommendation?.decision?.replace('_', ' ')}
                        </Text>
                        <Text style={styles.recExplanation}>{cleanText(recommendation?.explanation || "Reasoning pending review.")}</Text>

                        {(recommendation?.suggested_loan_limit || recommendation?.suggested_interest_rate) && (
                            <View style={{ marginTop: 15, borderTop: 1, borderColor: BORDER_COLOR, paddingTop: 10 }}>
                                <View style={{ flexDirection: 'row', marginBottom: 5 }}>
                                    <Text style={{ fontSize: 9, fontWeight: 'bold', width: 120 }}>Suggested Limit:</Text>
                                    <Text style={{ fontSize: 9 }}>{formatCurrency(recommendation?.suggested_loan_limit)}</Text>
                                </View>
                                <View style={{ flexDirection: 'row' }}>
                                    <Text style={{ fontSize: 9, fontWeight: 'bold', width: 120 }}>Target APR:</Text>
                                    <Text style={{ fontSize: 9 }}>{recommendation?.suggested_interest_rate}%</Text>
                                </View>
                            </View>
                        )}
                    </View>
                </View>

                {/* Advisory Disclaimer */}
                <View style={{ marginTop: 'auto', backgroundColor: BG_SLATE_50, padding: 10, borderRadius: 4 }}>
                    <Text style={{ fontSize: 8, fontWeight: 'bold', marginBottom: 4 }}>ADVISORY DISCLAIMER</Text>
                    <Text style={{ fontSize: 7, color: SLATE_LIGHT, lineHeight: 1.4 }}>
                        This Credit Appraisal Memorandum (CAM) is generated by Intelli-Credit's automated intelligence pipeline.
                        It utilizes deterministic modeling and probabilistic language processing for research synthesis.
                        This report is advisory in nature and must be ratified by an authorized credit committee.
                        Intelli-Credit assumes no liability for lending outcomes based on this report.
                    </Text>
                </View>

                {/* Footer */}
                <View style={styles.footer} fixed>
                    <Text style={styles.footerText}>INTELLI-CREDIT CONFIDENTIAL | GEN-ID: {data.analysis_id || 'N/A'}</Text>
                    <Text style={styles.footerText} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
                </View>
            </Page>
        </Document>
    );
};
