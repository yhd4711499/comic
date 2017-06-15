function unsuan(s) 
{
	sw="163.com|dmeden.com";
	su = location.hostname.toLowerCase();
	b=false;
	for(i=0;i<sw.split("|").length;i++) {
	    if(su.indexOf(sw.split("|")[i])>-1) {
	        b=true;
	        break;
        }
    }
    if(!b)return "";
    
    x = s.substring(s.length-1);
    w="abcdefghijklmnopqrstuvwxyz";
    xi=w.indexOf(x)+1;
    sk = s.substring(s.length-xi-12,s.length-xi-1);
    s=s.substring(0,s.length-xi-12);    
	k=sk.substring(0,sk.length-1);
	f=sk.substring(sk.length-1);
	for(i=0;i<k.length;i++) {
	    eval("s=s.replace(/"+ k.substring(i,i+1) +"/g,'"+ i +"')");
	}
    ss = s.split(f);
	s="";
	for(i=0;i<ss.length;i++) {
	    s+=String.fromCharCode(ss[i]);
    }
    return s;
}

var cuImg;

function window_onload()
{
    if(document.getElementById("btnPagePrv").disabled)
        document.getElementById("btnPagePrv2").disabled = true;
    if(document.getElementById("btnPageNext").disabled)
        document.getElementById("btnPageNext2").disabled = true;
    
    cuImg = getCuImg();
    cuImg.src = unsuan(cuImg.name);
	cuImg.style.cursor = "hand";
    //var evt = window.event;
    cuImg.onmousedown = function(evt){drag(evt);};
}

function getCuImg()
{
    if(document.getElementById("img1021")) return document.getElementById("img1021");
    if(document.getElementById("img2391")) return document.getElementById("img2391");
    if(document.getElementById("img7652")) return document.getElementById("img7652");
    if(document.getElementById("imgCurr")) return document.getElementById("imgCurr");
    return null;
}

function addFav()
{
    var sID = document.getElementById("hdVolID").value;
    if(sID == "")
    {
        alert("錯誤，找不到本漫畫記錄ID");
        return;
    }
    var url = "/ax/addFav.aspx?VolID=" + sID;   
   // window.open(url);
    var callback = addFav_callback;
    var data = "";
    Request.reSend(url,data,callback);
}
function addFav_callback(o)
{
    if(o == null)
    {
        alert("未知錯誤，無法收藏");
        return;
    }
    var s = o.responseText;
    alert(s);
}

function pageChange(s)
{
    if(s == "prv")
        document.getElementById("btnPagePrv").click();
    if(s == "next")        
         document.getElementById("btnPageNext").click();
}

function movePage(obj)
{
	var s1 = obj.src;
	if(s1.indexOf(".gif") < 0)
	{
		//document.body.scrollLeft = obj.width
		//document.body.scrollTop = 0;
	}
}

function prvLoadNext()
{
	if(document.getElementById("hdNextImg") != null)
	{
	var sNextImgName = document.getElementById("hdNextImg").value;
	sNextImgName = unsuan(sNextImgName);
	if(sNextImgName == "") return;
	if(document.getElementById("spMsg") != null)
		document.getElementById("spMsg").innerHTML = "正在讀取下一頁漫畫...";
	if(document.getElementById("spTmp") != null)
		document.getElementById("spTmp").innerHTML = "<img style='display:none' src='"+ sNextImgName +"' onload='prvLoadNextOK()' onerror='prvLoadNextErr()'>";
	window.status = "開始預讀下頁漫畫....";
	}
	
}
function prvLoadNextOK()
{
	document.getElementById("spMsg").innerHTML = "預讀完畢";
	window.status = "預讀完畢";
}
function prvLoadNextErr()
{
	document.getElementById("spMsg").innerHTML = "無法預讀下一頁漫畫！";
}


function initImg()
{

	
}	

function drag(evt) 
{
   
	evt = evt || window.event;
	if (document.all && evt.button != 1) {
		return false;
	}
		
	oX = 2 * document.documentElement.scrollLeft;
	cX = document.documentElement.scrollLeft - evt.screenX;
	oY = 2 * document.documentElement.scrollTop;
	cY = document.documentElement.scrollTop - evt.screenY;	
	if (cuImg.addEventListener) {
		cuImg.addEventListener("mousemove", moveHandler, true);
		cuImg.addEventListener("mouseup", upHandler, true);
	} else if (cuImg.attachEvent) {
		cuImg.setCapture( );
		cuImg.attachEvent("onmousemove", moveHandler);
		cuImg.attachEvent("onmouseup", upHandler);
		cuImg.attachEvent("onlosecapture", upHandler);
	} else {
		var oldmovehandler = cuImg.onmousemove;
		var olduphandler = cuImg.onmouseup;
		cuImg.onmousemove = moveHandler;
		cuImg.onmouseup = upHandler;
	}	
	if (evt.stopPropagation) evt.stopPropagation( );
	else evt.cancelBubble = true;	
	if (evt.preventDefault) evt.preventDefault( );
	else evt.returnValue = false;	
	if (evt.stopPropagation) evt.stopPropagation( );
	else evt.cancelBubble = true;	
	cuImg.style.cursor = "move";	
	function moveHandler(evt) {
		mX = evt.screenX + cX;
		mY = evt.screenY + cY;
		window.scrollTo(oX - mX, oY - mY);		
		if (evt.stopPropagation) evt.stopPropagation( );
		else evt.cancelBubble = true;
	}	
	function upHandler(evt) {
		cuImg.style.cursor = "pointer";		
		if (cuImg.removeEventListener) {
			cuImg.removeEventListener("mouseup", upHandler, true);
			cuImg.removeEventListener("mousemove", moveHandler, true);
		} else if (cuImg.detachEvent) {
			cuImg.detachEvent("onlosecapture", upHandler);
			cuImg.detachEvent("onmouseup", upHandler);
			cuImg.detachEvent("onmousemove", moveHandler);
			cuImg.releaseCapture( );
		} else {
			cuImg.onmouseup = olduphandler;
			cuImg.onmousemove = oldmovehandler;
		}
		if (evt.stopPropagation) evt.stopPropagation( );
		else evt.cancelBubble = true;
	}
}


function PageGo(lktype)
{
    
	try
	{
		var sID = document.getElementById("hdVolID").value;
		var s = document.getElementById("hdS").value;
		var nCurrNo = parseInt(document.getElementById("hdPageIndex").value);
		var nDataCount = parseInt(document.getElementById("hdPageCount").value);
		
		//alert(nCurrNo)
		if(lktype == "first")
		{
			location.href = "../"+ sID +"/1.html?s=" + s;	
		}
		else if(lktype == "prev")
		{
			if(nCurrNo == 1)
				alert("當前是第一頁")
			else			
				location.href = "../"+ sID +"/"+ (nCurrNo - 1)  + ".html?s=" + s;	
		}
		else if(lktype == "next")
		{
			if(nCurrNo >= nDataCount)
				alert("已經最後一頁")
			else			
				location.href = "../"+ sID +"/"+ (nCurrNo + 1)  + ".html?s=" + s;	
		}
		else if(lktype == "last")
		{
			location.href = "../"+ sID +"/"+ nDataCount +".html?s=" + s;	
		}
		else if(lktype == "Go")
		{
			var nGoPage = document.getElementById("ddlPageList").options[document.getElementById("ddlPageList").selectedIndex +1].value
			if(nGoPage != "")
				location.href = "../"+ sID +"/"+ nGoPage +".html?s=" + s;	
		}
	}
	catch(e)
	{
		return false;
	}
	
}	

function errRep()
{
        
     var htmurl= "http://b.99mh.com/?errurl=" + location.href;

     JqueryDialog.Open("漫畫報錯", htmurl, 640, 480);
        
}