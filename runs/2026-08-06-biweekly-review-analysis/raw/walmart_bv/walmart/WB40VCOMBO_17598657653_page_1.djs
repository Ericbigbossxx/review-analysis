$BV.Internal.ajaxCallback(function(url,apiConfig){
if(!/(^|\.)(bazaarvoice\.com|crossmediaservices\.com|retaillink\.cz|shoplocal\.com|tryitsampling\.com|wal\-mart\.com|wal\-mart\.com\.cn|wallmart\.com|wallmartphoto\.com|walmart\.com|walmartimages\.com)(:\d+)?$/.test(location.hostname)){
throw "Bazaarvoice: Permission denied";
}
$BV.Internal.configureAppLoader("rr",false,{"cmn/1336/analyticsInternalHooks":"analyticsHooks","cmn/1336/photoUpload":"photoUpload","cmn/1336temp/analyticsInternalHooks":"analyticsHooks","cmn/1336/ratingControls":"ratingControls"});
$BV.Internal.require(["rr/injection.rr","requester","feedback","domUtils","rr/analyticsInternalLegacyHooksRR","browserVersion","mediaGallery","rr/analyticsHooksRR","contentDisplay","jquery.core","dropdown","parseUri","cookies","analyticsVersioning","analyticsHooks","cmn/1336temp/analyticsInternalHooks","cmn/1336/analyticsInternalHooks","magpie","magpieTracking","analyticsAutoTagHooks","animationOptions","socialConnect","facebookConnect","facebookOpenGraph","jquery.ui.core","jquery.ui.widget","jquery.effects.core","positioners","contentDispatcher","wrapperDivs"],function(Injection){
var materials={"BVRRRatingSummarySourceID":" <div class=\"BVRRRootElement\">\n<div class=\"BVRRRatingSummary BVRRPrimarySummary BVRRPrimaryRatingSummary\"><div class=\"BVRRRatingSummaryStyle2\"><div class=\"BVRRRatingSummaryNoReviews\"> <div id=\"BVRRRatingSummaryLinkWriteFirstID\" class=\"BVRRRatingSummaryLink BVRRRatingSummaryLinkWriteFirst\">\n <span class=\"BVRRRatingSummaryLinkWriteFirstPrefix\">Be the first to<\/span>\n<a data-bvjsref=\"https://walmart.ugc.bazaarvoice.com/submit/1336/17598657653/writereview.djs?authsourcetype=__AUTHTYPE__&amp;campaignid=BV_RATING_SUMMARY_ZERO_REVIEWS&amp;format=embeddedhtml&amp;innerreturn=https%3A%2F%2Fwalmart.ugc.bazaarvoice.com%2F1336%2F17598657653%2Freviews.djs%3Fformat%3Dembeddedhtml%26num%3D100%26sort%3DsubmissionTime&amp;return=__RETURN__&amp;sessionparams=__BVSESSIONPARAMS__&amp;submissionparams=__BVSUBMISSIONPARAMETERS__&amp;submissionurl=__BVSUBMISSIONURL__&amp;user=__USERID__\" data-bvcfg=\"__CONFIGKEY__\" name=\"BV_TrackingTag_Rating_Summary_1_WriteReview_17598657653\" href=\"javascript://\">write a review<\/a><span class=\"BVRRRatingSummaryLinkWriteFirstSuffix\">|<\/span> <\/div>\n<\/div><\/div><\/div><a data-bvjsref=\"https://walmart.ugc.bazaarvoice.com/submit/1336/17598657653/writereview.djs?authsourcetype=__AUTHTYPE__&amp;campaignid=BV_SUBMISSIONLINK&amp;format=embeddedhtml&amp;innerreturn=https%3A%2F%2Fwalmart.ugc.bazaarvoice.com%2F1336%2F17598657653%2Freviews.djs%3Fformat%3Dembeddedhtml%26num%3D100%26sort%3DsubmissionTime&amp;return=__RETURN__&amp;sessionparams=__BVSESSIONPARAMS__&amp;submissionparams=__BVSUBMISSIONPARAMETERS__&amp;submissionurl=__BVSUBMISSIONURL__&amp;user=__USERID__\" data-bvcfg=\"__CONFIGKEY__\" style=\"display: none;\" href=\"javascript://\" id=\"BVSubmissionLink\"><\/a>\n <\/div>\n","BVRRSecondaryRatingSummarySourceID":" <div class=\"BVRRRootElement\">\n<div class=\"BVRRRatingSummary BVRRSecondaryRatingSummary\">\n\n<div class=\"BVRRRatingSummary BVRRPrimaryRatingSummary\"><div class=\"BVRRRatingSummaryStyle2\"><div class=\"BVRRRatingSummaryNoReviews\"> <div id=\"BVRRRatingSummaryLinkWriteFirstID\" class=\"BVRRRatingSummaryLink BVRRRatingSummaryLinkWriteFirst\">\n <span class=\"BVRRRatingSummaryLinkWriteFirstPrefix\">Be the first to<\/span>\n<a data-bvjsref=\"https://walmart.ugc.bazaarvoice.com/submit/1336/17598657653/writereview.djs?authsourcetype=__AUTHTYPE__&amp;campaignid=BV_RATING_SUMMARY_ZERO_REVIEWS&amp;format=embeddedhtml&amp;innerreturn=https%3A%2F%2Fwalmart.ugc.bazaarvoice.com%2F1336%2F17598657653%2Freviews.djs%3Fformat%3Dembeddedhtml%26num%3D100%26sort%3DsubmissionTime&amp;return=__RETURN__&amp;sessionparams=__BVSESSIONPARAMS__&amp;submissionparams=__BVSUBMISSIONPARAMETERS__&amp;submissionurl=__BVSUBMISSIONURL__&amp;user=__USERID__\" data-bvcfg=\"__CONFIGKEY__\" name=\"BV_TrackingTag_Rating_Summary_2_WriteReview_17598657653\" href=\"javascript://\">write a review<\/a><span class=\"BVRRRatingSummaryLinkWriteFirstSuffix\">|<\/span> <\/div>\n<\/div><\/div><\/div><\/div> <\/div>\n","BVRRSourceID":" <div id=\"BVRRWidgetID\" class=\"BVRRRootElement BVRRWidget\">\n<div id=\"BVRRContentContainerID\" class=\"BVRRContainer\"> \r\n\r\n\r\n\r\n\n\r\n<div id=\"BVRRDisplayContentID\" class=\"BVRRDisplayContent\"><div id=\"BVRRDisplayContentHeaderID\" class=\"BVRRHeader BVRRDisplayContentHeader\"><div class=\"BVRRDisplayContentHeaderContent\"><span id=\"BVRRDisplayContentTitleID\" class=\"BVRRTitle BVRRDisplayContentTitle\">Product Reviews<\/span><span id=\"BVRRDisplayContentSubtitleID\" class=\"BVRRSubtitle BVRRDisplayContentSubtitle\"><span id=\"BVRRDisplayContentLinkWriteID\" class=\"BVRRContentLink BVRRDisplayContentLinkWrite\"><a data-bvjsref=\"https://walmart.ugc.bazaarvoice.com/submit/1336/17598657653/writereview.djs?authsourcetype=__AUTHTYPE__&amp;campaignid=BV_REVIEW_DISPLAY&amp;format=embeddedhtml&amp;innerreturn=https%3A%2F%2Fwalmart.ugc.bazaarvoice.com%2F1336%2F17598657653%2Freviews.djs%3Fformat%3Dembeddedhtml%26num%3D100%26sort%3DsubmissionTime&amp;return=__RETURN__&amp;sessionparams=__BVSESSIONPARAMS__&amp;submissionparams=__BVSUBMISSIONPARAMETERS__&amp;submissionurl=__BVSUBMISSIONURL__&amp;user=__USERID__\" data-bvcfg=\"__CONFIGKEY__\" name=\"BV_TrackingTag_Review_Display_WriteReview\" href=\"javascript://\" title=\"Write a Review\">Write a Review<\/a><\/span><\/span><span class=\"BVRRSortAndSearch\"><\/span><\/div><\/div><div id=\"BVRRDisplayContentBodyID\" class=\"BVRRDisplayContentBody\"><div id=\"BVRRDisplayContentNoReviewsID\" class=\"BVRRDisplayContentNoReviews\"> <ul id=\"BVSEO_meta\" style=\"display:none!important\">\n <li data-bvseo=\"bvDateModified\">2026-08-05 T00:34:11.698-05:00<\/li>\n <li data-bvseo=\"ps\">bvseo_pps, prod_bvrr, vn_prr_5.6<\/li>\n <li data-bvseo=\"cp\">cp-1, bvpage1<\/li>\n <li data-bvseo=\"co\">co_noreviews, tv_0, tr_0<\/li>\n <li data-bvseo=\"cf\">loc_en_US, sid_17598657653, prod, sort_submissionTime<\/li>\n <\/ul>\n<\/div><\/div><div id=\"BVRRDisplayContentFooterID\" class=\"BVRRFooter BVRRDisplayContentFooter\"><\/div><div class=\"BVRRSpacer BVRRDisplayContentSpacer\"><\/div><\/div>\r\n<\/div>\r\n <\/div>\n"},
initializers={"BVRRRatingSummarySourceID":[{"init":"bindJsLinks","data":{},"module":"requester"}],"BVRRSecondaryRatingSummarySourceID":[{"init":"bindJsLinks","data":{},"module":"requester"}],"BVRRSourceID":[{"init":"bindJsLinks","data":{},"module":"requester"}]},
widgets={};
widgets["content"]={"sourceId":"BVRRSourceID","handledContentTypes":["Review","Comment"],"containerId":"BVRRContainer"};
if((typeof(window['BVRR_17598657653_MediaGalleryObject']) != 'object') || !window['BVRR_17598657653_MediaGalleryObject'].isRendered()){
widgets["mediaGallery"]={"sourceId":"BVRRMediaGallerySourceID","containerId":"BVRRMediaGalleryContainer"};
}
widgets["secondarySummary"]={"sourceId":"BVRRSecondaryRatingSummarySourceID","containerId":"BVRRSecondarySummaryContainer"};
widgets["summary"]={"sourceId":"BVRRRatingSummarySourceID","containerId":"BVRRSummaryContainer"};
var injectionData={
apiConfig:apiConfig,
bvstateInfo:"p/17598657653",
canonicalTags:false,
containerInitializer:false,
cookiePath:"/",
crossDomainUrl:"https://walmart.ugc.bazaarvoice.com/1336/crossdomain.htm?format=embedded",
embeddedUrl:url,
globalInitializers:[{"module":"browserVersion","init":"initialize","data":{"useBodyTag":false,"containerId":"BVRRSummaryContainer"}},{"module":"browserVersion","init":"initialize","data":{"useBodyTag":false,"containerId":"BVRRSecondarySummaryContainer"}},{"module":"browserVersion","init":"initialize","data":{"useBodyTag":false,"containerId":"BVRRContainer"}},{"module":"dropdown","init":"addSelectHandlers","data":{"dropdownsName":"BV_TrackingTag_Review_Display_Sort"}},{"module":"feedback","init":"onInjection","data":{"options":{"cookiePrefixes":{"Voting":"pfv"},"contentFocusing":{},"cookiePath":"/"},"id":"Product_b1a49xm2l2s95fm23py2ivzgd"}},{"module":"feedback","init":"onInjection","data":{"options":{"cookiePrefixes":{"Voting":"rfv","Inappropriate":"rif"},"contentFocusing":{},"cookiePath":"/"},"id":"Review_b1a49xm2l2s95fm23py2ivzgd"}},{"module":"feedback","init":"onInjection","data":{"options":{"cookiePrefixes":{"Voting":"cfv","Inappropriate":"cif"},"contentFocusing":{},"cookiePath":"/"},"id":"ReviewComment_b1a49xm2l2s95fm23py2ivzgd"}}],
gotoCookieRegexp:/^https?:\/\/[^/?#]+(\/[^?#]*)\//,
inFrameSubmissionEnabled:false,
pageIdPrefix:"BVRR",
pageTrackers:[],
postInjectionFunction:function(Inject){
window.bvScrollToElement();
(function() {
if (typeof(window['BVRR_17598657653_MediaGalleryObject']) == 'object') {
window['BVRR_17598657653_MediaGalleryObject'].sync();
} else {
window['BVRR_17598657653_MediaGalleryObject'] = window.newBVMediaGallery('BVRR_17598657653_MediaGallery', 0,
0, false, 'https://walmart.ugc.bazaarvoice.com/1336/17598657653/mediagallery.djs?format=embeddedhtml',
true, { name : 'centerWithinAnchor', args : ['<POPIN_ID>', 'BVRRWidgetID', 10] }
,
[]);
}
})();
},
productId:"17598657653",
replaceDisplayTokens:true,
replacementsPrefix:"BVRR",
replaceSessionParameters:false,
returnURLFixedValue:"",
returnURLForceRelativeToRoot:true,
setWindowTitle:false,
soiContainerID:"BVRRContentValidationID_17598657653",
soiContentIDs:[],
sviParameterName:"bvrrp",
sviRedirectBaseUrl:"https://walmart.ugc.bazaarvoice.com/1336/",
webAnalyticsConfig:{"customTrackedObjectsSelector":"","jsonData":{"bvDisplayCode":"1336","deploymentZone":"main_site","autoTagAnalyticsConfiguration":{"trackSubmissionPageLoads":true,"trackFormActions":true,"autoTagAnalyticsVersion":"5.0","vendors":[{"vendorName":"omniture","eventNum":38,"eVarNum":48,"trackerReference":"s_omni","brandVoiceTrackingType":null,"brandVoiceTrackingEVarNum":0},{"vendorName":"magpie","anonymous":false,"brandDomain":"false","defaultClassesOnly":false}],"productTracking":{"tracking":true,"initialProductDisplay":false}},"userLocale":"en_US","productId":"17598657653","eType":"Read","subjectType":"Product","bvAnalyticsVersion":"4.7","rootCategoryId":"Tools&Hardware-Power&HandTools-StringTrimmers","analyticsWhitespaceTrackingEnabled":true,"bvProduct":"RatingsAndReviews","attributes":{"numReviews":0,"avgRating":0E-12,"numRatingsOnlyReviews":0,"percentRecommend":0},"ciTrackingEnabled":false,"bvClientName":"walmart","brand":"wild badger power","leafCategoryId":"Tools&Hardware-Power&HandTools-StringTrimmers","bvExtension":{}},"customizersName":"BVRRAnalyticsCustomizers","SIWZeroDeployEnabled":false,"conversionTracking":{"conversionTrackingElementSelector":null,"conversionTrackingMetadataSelector":null,"conversionTrackingParseRegexp":null,"conversionTrackingName":"AddToCart"},"maxTrackingTagTraversalDepth":3,"customContainersFnName":"BVRRAnalyticsCustomContainers","customTrackedObjects":""},
widgetInitializers:initializers,
widgetLimit:-1,
widgetMaterials:materials,
widgetMetadata:widgets,
windowTitle:null};
Injection.newInstance().apiInjection(injectionData);
});
});